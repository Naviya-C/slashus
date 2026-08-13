#!/usr/bin/env bash
set -euo pipefail
OUT="src/agentic_service/proto_gen"
mkdir -p "$OUT"; touch "$OUT/__init__.py"
python -m grpc_tools.protoc -I proto --python_out="$OUT" --pyi_out="$OUT" \
  --grpc_python_out="$OUT" proto/search.proto
sed -i.bak 's/^import search_pb2 as/from . import search_pb2 as/' "$OUT/search_pb2_grpc.py"
rm -f "$OUT/search_pb2_grpc.py.bak"
echo "stubs regenerated in $OUT"
