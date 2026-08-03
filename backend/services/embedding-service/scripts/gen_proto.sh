#!/usr/bin/env bash
# Regenerate the gRPC stubs from proto/search.proto.
#
# Run this after ANY change to the proto, and run it in agentic-service too —
# the two copies of search.proto must stay byte-identical or the services
# disagree about the wire format in ways that only surface at runtime.
set -euo pipefail

cd "$(dirname "$0")/.."

python -m grpc_tools.protoc \
  --proto_path=proto \
  --python_out=embedding_service \
  --grpc_python_out=embedding_service \
  proto/search.proto

# protoc emits `import search_pb2` — a top-level import that only resolves if
# embedding_service/ happens to be on sys.path. Inside the package it is not.
if [[ "$(uname)" == "Darwin" ]]; then
  sed -i '' 's/^import search_pb2 as search__pb2$/from embedding_service import search_pb2 as search__pb2/' \
    embedding_service/search_pb2_grpc.py
else
  sed -i 's/^import search_pb2 as search__pb2$/from embedding_service import search_pb2 as search__pb2/' \
    embedding_service/search_pb2_grpc.py
fi

echo "regenerated embedding_service/search_pb2{,_grpc}.py"
echo
echo "Now copy proto/search.proto to agentic-service/proto/ and run its"
echo "scripts/gen_proto.sh, or the two services will drift."
