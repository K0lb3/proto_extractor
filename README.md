This module extracts .proto files from compiled applications and memory dumps

## How it works

Protobuf stores an encoded version of the original .proto file as string named ``descriptor_table_protodef_{encoded_file_name}``.
The encoded version is actually the parsed .proto file encoded via protobuf itself, namely via the [descriptor.proto](https://github.com/protocolbuffers/protobuf/blob/master/src/google/protobuf/descriptor.proto).

This encoded version is always created, besides if the original .proto contained following option:
``option optimize_for = LITE_RUNTIME;```, which removes descriptors and reflection.


Since the structure of the encoded proto aka descriptor is known, all that has to be done to extract .proto files from an app, is looking for specific patterns and then trying to parse that place via the descriptor proto.

## TODO

- add setup
- add to path
- more agressive extration