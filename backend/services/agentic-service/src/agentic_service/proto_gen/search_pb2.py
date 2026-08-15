"""Generated protocol buffer code."""

from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC, 7, 35, 1, "", "search.proto"
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x0csearch.proto\x12\x11slashus.search.v2"\x1e\n\x0c\x46ilterValues\x12\x0e\n\x06values\x18\x01 \x03(\t"\x9f\x02\n\rSearchRequest\x12\r\n\x05query\x18\x01 \x01(\t\x12\x0f\n\x07user_id\x18\x02 \x01(\t\x12\x0f\n\x07\x64oc_ids\x18\x03 \x03(\t\x12\r\n\x05limit\x18\x04 \x01(\x05\x12+\n\x04mode\x18\x05 \x01(\x0e\x32\x1d.slashus.search.v2.SearchMode\x12\x10\n\x08language\x18\x06 \x01(\t\x12>\n\x07\x66ilters\x18\x07 \x03(\x0b\x32-.slashus.search.v2.SearchRequest.FiltersEntry\x1aO\n\x0c\x46iltersEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12.\n\x05value\x18\x02 \x01(\x0b\x32\x1f.slashus.search.v2.FilterValues:\x02\x38\x01"\xfd\x01\n\x03Hit\x12\x10\n\x08\x63hunk_id\x18\x01 \x01(\t\x12\r\n\x05score\x18\x02 \x01(\x02\x12\x0f\n\x07\x63ontent\x18\x03 \x01(\t\x12\r\n\x05title\x18\x04 \x01(\t\x12\x0c\n\x04page\x18\x05 \x01(\x05\x12\x0e\n\x06\x64oc_id\x18\x06 \x01(\t\x12\x0e\n\x06source\x18\x07 \x01(\t\x12\x30\n\x05\x65xtra\x18\x08 \x03(\x0b\x32!.slashus.search.v2.Hit.ExtraEntry\x12\x12\n\ndense_rank\x18\t \x01(\x05\x12\x13\n\x0bsparse_rank\x18\n \x01(\x05\x1a,\n\nExtraEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01"\xcb\x01\n\x0eSearchResponse\x12$\n\x04hits\x18\x01 \x03(\x0b\x32\x16.slashus.search.v2.Hit\x12\x17\n\x0f\x63ollection_used\x18\x02 \x01(\t\x12\x15\n\rlanguage_used\x18\x03 \x01(\t\x12\x1d\n\x15user_has_no_documents\x18\x04 \x01(\x08\x12\x19\n\x11total_user_chunks\x18\x05 \x01(\x05\x12\x17\n\x0f\x66ilters_applied\x18\x06 \x03(\t\x12\x10\n\x08\x64\x65graded\x18\x07 \x01(\x08"D\n\x11ListTitlesRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\t\x12\x0f\n\x07\x64oc_ids\x18\x02 \x03(\t\x12\r\n\x05limit\x18\x03 \x01(\x05"/\n\tTitleInfo\x12\r\n\x05title\x18\x01 \x01(\t\x12\x13\n\x0b\x63hunk_count\x18\x02 \x01(\x05"k\n\x12ListTitlesResponse\x12,\n\x06titles\x18\x01 \x03(\x0b\x32\x1c.slashus.search.v2.TitleInfo\x12\x14\n\x0ctotal_chunks\x18\x02 \x01(\x05\x12\x11\n\ttruncated\x18\x03 \x01(\x08"O\n\x0c\x45mbedRequest\x12\r\n\x05texts\x18\x01 \x03(\t\x12\x30\n\x07purpose\x18\x02 \x01(\x0e\x32\x1f.slashus.search.v2.EmbedPurpose"\x1d\n\x0b\x44\x65nseVector\x12\x0e\n\x06values\x18\x01 \x03(\x02"/\n\x0cSparseVector\x12\x0f\n\x07indices\x18\x01 \x03(\r\x12\x0e\n\x06values\x18\x02 \x03(\x02"\x92\x01\n\rEmbedResponse\x12-\n\x05\x64\x65nse\x18\x01 \x03(\x0b\x32\x1e.slashus.search.v2.DenseVector\x12/\n\x06sparse\x18\x02 \x03(\x0b\x32\x1f.slashus.search.v2.SparseVector\x12\r\n\x05model\x18\x03 \x01(\t\x12\x12\n\ndimensions\x18\x04 \x01(\x05*p\n\nSearchMode\x12\x1b\n\x17SEARCH_MODE_UNSPECIFIED\x10\x00\x12\x16\n\x12SEARCH_MODE_HYBRID\x10\x01\x12\x15\n\x11SEARCH_MODE_DENSE\x10\x02\x12\x16\n\x12SEARCH_MODE_SPARSE\x10\x03*b\n\x0c\x45mbedPurpose\x12\x1d\n\x19\x45MBED_PURPOSE_UNSPECIFIED\x10\x00\x12\x17\n\x13\x45MBED_PURPOSE_QUERY\x10\x01\x12\x1a\n\x16\x45MBED_PURPOSE_DOCUMENT\x10\x02\x32\x84\x02\n\x0cVectorSearch\x12M\n\x06Search\x12 .slashus.search.v2.SearchRequest\x1a!.slashus.search.v2.SearchResponse\x12Y\n\nListTitles\x12$.slashus.search.v2.ListTitlesRequest\x1a%.slashus.search.v2.ListTitlesResponse\x12J\n\x05\x45mbed\x12\x1f.slashus.search.v2.EmbedRequest\x1a .slashus.search.v2.EmbedResponseB1Z/github.com/slashus/contracts/search/v2;searchv2b\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "search_pb2", _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    _globals["DESCRIPTOR"]._loaded_options = None
    _globals[
        "DESCRIPTOR"
    ]._serialized_options = b"Z/github.com/slashus/contracts/search/v2;searchv2"
    _globals["_SEARCHREQUEST_FILTERSENTRY"]._loaded_options = None
    _globals["_SEARCHREQUEST_FILTERSENTRY"]._serialized_options = b"8\001"
    _globals["_HIT_EXTRAENTRY"]._loaded_options = None
    _globals["_HIT_EXTRAENTRY"]._serialized_options = b"8\001"
    _globals["_SEARCHMODE"]._serialized_start = 1357
    _globals["_SEARCHMODE"]._serialized_end = 1469
    _globals["_EMBEDPURPOSE"]._serialized_start = 1471
    _globals["_EMBEDPURPOSE"]._serialized_end = 1569
    _globals["_FILTERVALUES"]._serialized_start = 35
    _globals["_FILTERVALUES"]._serialized_end = 65
    _globals["_SEARCHREQUEST"]._serialized_start = 68
    _globals["_SEARCHREQUEST"]._serialized_end = 355
    _globals["_SEARCHREQUEST_FILTERSENTRY"]._serialized_start = 276
    _globals["_SEARCHREQUEST_FILTERSENTRY"]._serialized_end = 355
    _globals["_HIT"]._serialized_start = 358
    _globals["_HIT"]._serialized_end = 611
    _globals["_HIT_EXTRAENTRY"]._serialized_start = 567
    _globals["_HIT_EXTRAENTRY"]._serialized_end = 611
    _globals["_SEARCHRESPONSE"]._serialized_start = 614
    _globals["_SEARCHRESPONSE"]._serialized_end = 817
    _globals["_LISTTITLESREQUEST"]._serialized_start = 819
    _globals["_LISTTITLESREQUEST"]._serialized_end = 887
    _globals["_TITLEINFO"]._serialized_start = 889
    _globals["_TITLEINFO"]._serialized_end = 936
    _globals["_LISTTITLESRESPONSE"]._serialized_start = 938
    _globals["_LISTTITLESRESPONSE"]._serialized_end = 1045
    _globals["_EMBEDREQUEST"]._serialized_start = 1047
    _globals["_EMBEDREQUEST"]._serialized_end = 1126
    _globals["_DENSEVECTOR"]._serialized_start = 1128
    _globals["_DENSEVECTOR"]._serialized_end = 1157
    _globals["_SPARSEVECTOR"]._serialized_start = 1159
    _globals["_SPARSEVECTOR"]._serialized_end = 1206
    _globals["_EMBEDRESPONSE"]._serialized_start = 1209
    _globals["_EMBEDRESPONSE"]._serialized_end = 1355
    _globals["_VECTORSEARCH"]._serialized_start = 1572
    _globals["_VECTORSEARCH"]._serialized_end = 1832
# @@protoc_insertion_point(module_scope)
