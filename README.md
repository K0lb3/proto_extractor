This module extracts .proto files/structures from compiled applications and memory dumps

## Requirements

- Python 3.6+
- [protobuf](https://pypi.org/project/protobuf)

## Usage

### CLI

The setup adds a command line option to call the script.

```
usage: "proto_extractor - a protobuf structure extractor"

    Extraction Modes:
    - filename : try to find structures by looking for viable original filenames (less trash)
    - agressive : try to parse at every byte (more trash, but also more likely to find every message)"


positional arguments:
  mode        filename (default) or agressive
  src         path of the file to be scraped
  dst         dir where the recovered structures will be saved

optional arguments:
  -h, --help  show this help message and exit
```


### Module

You can also simply use proto_extractor as a normal module within python projects.

## How it works

Protobuf stores an encoded version of the original .proto file as string named ``descriptor_table_protodef_{encoded_file_name}``.
The encoded version is actually the parsed .proto file encoded via protobuf itself, namely via the [descriptor.proto](https://github.com/protocolbuffers/protobuf/blob/master/src/google/protobuf/descriptor.proto).

This encoded version is always created, besides if the original .proto contained following option:
``option optimize_for = LITE_RUNTIME;``, which removes descriptors and reflection.


Since the structure of the encoded proto aka descriptor is known, all that has to be done to extract .proto files from an app, is looking for specific patterns and then trying to parse that place via the descriptor proto.

## TODO

- add setup
- add to path
- more agressive extration
