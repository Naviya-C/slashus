# -*- coding: utf-8 -*-
# Generated protocol buffer code.  DO NOT EDIT BY HAND.
# source: search.proto
#
# Regenerate with:  ./scripts/gen_proto.sh
#
# NOTE: this file deliberately omits the `_runtime_version.Validate...` call
# that protoc >= 5.28 emits. That call pins a MINIMUM protobuf runtime and
# raises on import when the installed runtime is older — which turns a version
# skew between this service and embedding-service into an ImportError at
# startup rather than a warning. The descriptor itself is identical.
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0csearch.proto\x12\x11slashus.search.v1"\x1e\n\x0cFilterValues\x12\x0e\n\x06values\x18\x01 \x03(\t"\x9f\x02\n\rSearchRequest\x12\r\n\x05query\x18\x01 \x01(\t\x12\x0f\n\x07user_id\x18\x02 \x01(\t\x12\x0f\n\x07doc_ids\x18\x03 \x03(\t\x12\r\n\x05limit\x18\x04 \x01(\x05\x12+\n\x04mode\x18\x05 \x01(\x0e2\x1d.slashus.search.v1.SearchMode\x12\x10\n\x08language\x18\x06 \x01(\t\x12>\n\x07filters\x18\x07 \x03(\x0b2-.slashus.search.v1.SearchRequest.FiltersEntry\x1aO\n\x0cFiltersEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12.\n\x05value\x18\x02 \x01(\x0b2\x1f.slashus.search.v1.FilterValues:\x028\x01"\xfd\x01\n\x03Hit\x12\x10\n\x08chunk_id\x18\x01 \x01(\t\x12\r\n\x05score\x18\x02 \x01(\x02\x12\x0f\n\x07content\x18\x03 \x01(\t\x12\r\n\x05title\x18\x04 \x01(\t\x12\x0c\n\x04page\x18\x05 \x01(\x05\x12\x0e\n\x06doc_id\x18\x06 \x01(\t\x12\x0e\n\x06source\x18\x07 \x01(\t\x120\n\x05extra\x18\x08 \x03(\x0b2!.slashus.search.v1.Hit.ExtraEntry\x12\x12\n\ndense_rank\x18\t \x01(\x05\x12\x13\n\x0bsparse_rank\x18\n \x01(\x05\x1a,\n\nExtraEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x028\x01"\xb9\x01\n\x0eSearchResponse\x12$\n\x04hits\x18\x01 \x03(\x0b2\x16.slashus.search.v1.Hit\x12\x17\n\x0fcollection_used\x18\x02 \x01(\t\x12\x15\n\rlanguage_used\x18\x03 \x01(\t\x12\x1d\n\x15user_has_no_documents\x18\x04 \x01(\x08\x12\x19\n\x11total_user_chunks\x18\x05 \x01(\x05\x12\x17\n\x0ffilters_applied\x18\x06 \x03(\t"D\n\x11ListTitlesRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\t\x12\x0f\n\x07doc_ids\x18\x02 \x03(\t\x12\r\n\x05limit\x18\x03 \x01(\x05"/\n\tTitleInfo\x12\r\n\x05title\x18\x01 \x01(\t\x12\x13\n\x0bchunk_count\x18\x02 \x01(\x05"k\n\x12ListTitlesResponse\x12,\n\x06titles\x18\x01 \x03(\x0b2\x1c.slashus.search.v1.TitleInfo\x12\x14\n\x0ctotal_chunks\x18\x02 \x01(\x05\x12\x11\n\ttruncated\x18\x03 \x01(\x08"O\n\x0cEmbedRequest\x12\r\n\x05texts\x18\x01 \x03(\t\x120\n\x07purpose\x18\x02 \x01(\x0e2\x1f.slashus.search.v1.EmbedPurpose"\x1d\n\x0bDenseVector\x12\x0e\n\x06values\x18\x01 \x03(\x02"/\n\x0cSparseVector\x12\x0f\n\x07indices\x18\x01 \x03(\r\x12\x0e\n\x06values\x18\x02 \x03(\x02"o\n\rEmbedResponse\x12-\n\x05dense\x18\x01 \x03(\x0b2\x1e.slashus.search.v1.DenseVector\x12/\n\x06sparse\x18\x02 \x03(\x0b2\x1f.slashus.search.v1.SparseVector"\x0f\n\rHealthRequest"C\n\x0eHealthResponse\x12\r\n\x05ready\x18\x01 \x01(\x08\x12\x0e\n\x06detail\x18\x02 \x01(\t\x12\x12\n\nvocab_hash\x18\x03 \x01(\t*S\n\nSearchMode\x12\x16\n\x12SEARCH_MODE_HYBRID\x10\x00\x12\x15\n\x11SEARCH_MODE_DENSE\x10\x01\x12\x16\n\x12SEARCH_MODE_SPARSE\x10\x02*C\n\x0cEmbedPurpose\x12\x17\n\x13EMBED_PURPOSE_QUERY\x10\x00\x12\x1a\n\x16EMBED_PURPOSE_DOCUMENT\x10\x012\xd3\x02\n\x0cVectorSearch\x12M\n\x06Search\x12 .slashus.search.v1.SearchRequest\x1a!.slashus.search.v1.SearchResponse\x12Y\n\nListTitles\x12$.slashus.search.v1.ListTitlesRequest\x1a%.slashus.search.v1.ListTitlesResponse\x12J\n\x05Embed\x12\x1f.slashus.search.v1.EmbedRequest\x1a .slashus.search.v1.EmbedResponse\x12M\n\x06Health\x12 .slashus.search.v1.HealthRequest\x1a!.slashus.search.v1.HealthResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'search_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SEARCHREQUEST_FILTERSENTRY']._loaded_options = None
    _globals['_SEARCHREQUEST_FILTERSENTRY']._serialized_options = b'8\001'
    _globals['_HIT_EXTRAENTRY']._loaded_options = None
    _globals['_HIT_EXTRAENTRY']._serialized_options = b'8\001'
# @@protoc_insertion_point(module_scope)
