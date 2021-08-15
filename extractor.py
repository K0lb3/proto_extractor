from google.protobuf.message import DecodeError
from google.protobuf.descriptor_pb2 import FileDescriptorProto
import os
from enum import IntEnum
import re
from typing import Union


def extract_via_filename(src: Union[str, bytes], dst: str):
    """Extracts .proto messages from the source by looking for .proto filenames in the source.

    Args:
        src (str|bytes): The source that should be searched. Can be a filepath or bytes.
        dst (str): Destination folder where the reconstructed .proto files will be stored in.
    """
    if isinstance(src, str):
        with open(src, "rb") as f:
            data = f.read()
    else:
        data = src

    fdps = search_via_filename(data)
    for fdp in fdps:
        dump(fdp, dst)


def search_via_filename(data):
    found = []
    # FileDescriptor:
    # 1. 10 - name field - (0x01 << 3) | 2 - 2 wiretype for string
    # 2. length of name as varint
    # 3. name
    i = 0
    while i != -1:
        i = data.find(b".proto", i + 1)
        end = i + len(".proto")
        for j in range(255):  # name shouldn't be longer than that
            if data[i - j] == 10:
                break
        else:
            # only reaches here IF previous loop didn't break
            # so if no FieldDescriptor name field tag was found
            continue

        length, offset = read_varint(data, i - j + 1)
        filename = data[offset : offset + length]
        try:
            filename = filename.decode("utf8")
            fdp = FileDescriptorProto()
            fdp.ParseFromString(data[offset - 2 :])
            if fdp.name:
                found.append(fdp)
        except (UnicodeDecodeError, DecodeError):
            continue

    return found


def read_varint(data, off):
    shift = 0
    result = 0
    while True:
        i = data[off]
        off += 1
        result |= (i & 0x7F) << shift
        shift += 7
        if not (i & 0x80):
            break
    return result, off


def resolve_class_path(typ: str, namespace: list[str], msg_name: str):
    if typ[0] == ".":
        typ = typ[1:].split(".")
        for name in namespace:
            if typ[0] == name:
                typ.pop(0)
            else:
                break
        if typ[0] == msg_name:
            typ.pop(0)

        typ = ".".join(typ)
        if not typ:  # fix if parent message has the same name as the nested one
            typ = msg_name
    return typ


class Type(IntEnum):
    double = 1
    float = 2
    int64 = 3
    uint64 = 4
    int32 = 5
    fixed64 = 6
    fixed32 = 7
    bool = 8
    string = 9
    group = 10
    message = 11
    bytes = 12
    uint32 = 13
    enum = 14
    sfixed32 = 15
    sfixed64 = 16
    sint32 = 17
    sint64 = 18


class Label(IntEnum):
    optional = 1
    required = 2
    repeated = 3


def write_enum(f, enum, indent):
    f.write(f"{'  '*indent}enum {enum.name} {{\n")
    if enum.options:
        for option in str(enum.options).split("\n"):
            if option:
                f.write(f'{"  "*(indent+1)}option {option.replace(":"," =")};\n')

    for val in enum.value:
        f.write(f"{'  '*(indent+1)}{val.name} = {val.number};\n")
    f.write(f"{'  '*indent}}}\n\n")


def write_message(f, msg, indent, namespace):
    f.write(f"{'  '*indent}message {msg.name} {{\n")

    for enum in msg.enum_type:
        write_enum(f, enum, indent + 1)

    for msg_ in msg.nested_type:
        write_message(f, msg_, indent + 1, namespace + [msg.name])

    for extension in msg.extension:
        write_extension(f, extension, indent + 1, namespace + [msg.name])

    # dirty solution, but I couldn't figure out how to find all fields of a oneof
    oneof_fields = {None: [], **{i: [] for i in range(len(msg.oneof_decl))}}
    for field in msg.field:
        match = re.search(r"oneof_index: (\d+)", str(field))
        oneof_fields[int(match[1]) if match else None].append(field)

    for ind, oneof in enumerate(msg.oneof_decl):
        f.write(f"{'  '*(indent+1)}oneof {oneof.name} {{\n")
        for field in oneof_fields[ind]:
            write_field(f, indent + 2, field, namespace, msg.name)
        f.write(f"{'  '*(indent+1)}}}\n")

    for field in oneof_fields[None]:
        write_field(f, indent + 1, field, namespace, msg.name)

    if msg.reserved_range or msg.reserved_name:
        f.write(f"{'  '*(indent+1)}\n")
        if msg.reserved_range:
            ranges = [
                str(range.start)
                if range.start + 1 == range.end
                else f"{range.start} to {range.end-1}"
                for range in msg.reserved_range
            ]
            f.write(f'{"  "*(indent+1)}reserved {", ".join(ranges)};\n')

        if msg.reserved_name:
            f.write(
                '{}reserved "{}";\n'.format(
                    "  " * (indent + 1), '", "'.join(msg.reserved_name)
                )
            )

    if msg.extension_range:
        f.write(f"{'  '*(indent+1)}\n")
        ranges = [
            str(range.start)
            if range.start + 1 == range.end
            else f"{range.start} to {range.end-1}"
            for range in msg.extension_range
        ]
        f.write(f'{"  "*(indent+1)}extensions {", ".join(ranges)};\n\n')

    f.write(f"{'  '*indent}}}\n\n")


def write_field(f, indent, field, namespace, parent_name):
    options = []
    if field.default_value:
        val = field.default_value
        if field.type == Type.string:
            val = f'"{val}"'
        options.append(f"[default = {val}]")
    if field.options.packed:
        options.append("[packed = true]")
    if field.options.deprecated:
        options.append("[deprecated = true]")

    if field.type in [Type.message, Type.enum]:
        f.write(
            "{indent}{label} {type} {name} = {num}{options};\n".format(
                indent="  " * indent,
                label=Label(field.label).name,
                type=resolve_class_path(field.type_name, namespace, parent_name),
                name=field.name,
                num=field.number,
                options=(" " + " ".join(options)) if options else "",
            )
        )
    else:
        f.write(
            "{indent}{label} {type} {name} = {num}{options};\n".format(
                indent="  " * indent,
                label=Label(field.label).name,
                type=Type(field.type).name,
                name=field.name,
                num=field.number,
                options=(" " + " ".join(options)) if options else "",
            )
        )


def write_extension(f, ext, indent, namespace):
    extendee = resolve_class_path(
        ext.extendee, namespace, ""
    )  # maybe have to fix the class name
    f.write(f"{'  '*indent}extend {extendee} {{\n")
    write_field(f, indent + 1, ext, namespace, "")  # maybe have to fix the class name
    f.write(f"{'  '*indent}}}\n\n")


def dump(fdp: FileDescriptorProto, dst=""):
    ###############################
    # 1. find filename
    ###############################
    *dir, name = fdp.name.split("/")

    dir = os.path.join(dst, *dir)
    if dir:
        os.makedirs(dir, exist_ok=True)

    name, ext = os.path.splitext(name)
    if ext != ".proto":
        name += ext

    fp = os.path.join(dir, f"{name}.proto")
    i = 2
    while os.path.exists(fp):
        fp = os.path.join(dir, f"{name} ({i}).proto")
        i += 1

    ###############################
    # 2. write to file
    ###############################
    with open(fp, "wt", encoding="utf8") as f:
        # syntax - proto2 or proto3
        f.write(f'syntax = "{fdp.syntax if fdp.syntax else "proto2"}";\n\n')

        # package - namespace
        if fdp.package:
            f.write(f"package {fdp.package};\n\n")

        # compile options
        if fdp.options:
            for option in str(fdp.options).split("\n"):
                if option:
                    f.write(f'option {option.replace(":"," =")};\n')
            f.write("\n")

        # required imports
        if fdp.dependency:
            for dep in fdp.dependency:
                f.write(f'import "{dep}";\n')  # TODO : public?
            f.write("\n")

        # enums
        for enum in fdp.enum_type:
            write_enum(f, enum, 0)

        # messages
        for msg in fdp.message_type:
            write_message(f, msg, 0, fdp.package.split("."))

        # extensions
        for extension in fdp.extension:
            write_extension(f, extension, 0, fdp.package.split("."))

        # services
        for service in fdp.service:
            f.write(f"service {service.name} {{\n")
            for method in service.method:
                input_type = resolve_class_path(
                    method.input_type, fdp.package.split("."), service.name
                )
                output_type = resolve_class_path(
                    method.output_type, fdp.package.split("."), service.name
                )
                f.write(f"  rpc {method.name}({input_type} return ({output_type});\n")
            f.write(f"}}\n")


if __name__ == "__main__":
    pass
