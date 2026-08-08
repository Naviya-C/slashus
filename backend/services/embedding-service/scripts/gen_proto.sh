#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python -m grpc_tools.protoc \
  --proto_path=proto \
  --python_out=embedding_service \
  --grpc_python_out=embedding_service \
  proto/search.proto


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
