from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SearchMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SEARCH_MODE_UNSPECIFIED: _ClassVar[SearchMode]
    SEARCH_MODE_HYBRID: _ClassVar[SearchMode]
    SEARCH_MODE_DENSE: _ClassVar[SearchMode]
    SEARCH_MODE_SPARSE: _ClassVar[SearchMode]

class EmbedPurpose(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EMBED_PURPOSE_UNSPECIFIED: _ClassVar[EmbedPurpose]
    EMBED_PURPOSE_QUERY: _ClassVar[EmbedPurpose]
    EMBED_PURPOSE_DOCUMENT: _ClassVar[EmbedPurpose]

SEARCH_MODE_UNSPECIFIED: SearchMode
SEARCH_MODE_HYBRID: SearchMode
SEARCH_MODE_DENSE: SearchMode
SEARCH_MODE_SPARSE: SearchMode
EMBED_PURPOSE_UNSPECIFIED: EmbedPurpose
EMBED_PURPOSE_QUERY: EmbedPurpose
EMBED_PURPOSE_DOCUMENT: EmbedPurpose

class FilterValues(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ("query", "user_id", "doc_ids", "limit", "mode", "language", "filters")
    class FiltersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: FilterValues
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[_Union[FilterValues, _Mapping]] = ...
        ) -> None: ...

    QUERY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DOC_IDS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    query: str
    user_id: str
    doc_ids: _containers.RepeatedScalarFieldContainer[str]
    limit: int
    mode: SearchMode
    language: str
    filters: _containers.MessageMap[str, FilterValues]
    def __init__(
        self,
        query: _Optional[str] = ...,
        user_id: _Optional[str] = ...,
        doc_ids: _Optional[_Iterable[str]] = ...,
        limit: _Optional[int] = ...,
        mode: _Optional[_Union[SearchMode, str]] = ...,
        language: _Optional[str] = ...,
        filters: _Optional[_Mapping[str, FilterValues]] = ...,
    ) -> None: ...

class Hit(_message.Message):
    __slots__ = (
        "chunk_id",
        "score",
        "content",
        "title",
        "page",
        "doc_id",
        "source",
        "extra",
        "dense_rank",
        "sparse_rank",
    )
    class ExtraEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

    CHUNK_ID_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    DOC_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    DENSE_RANK_FIELD_NUMBER: _ClassVar[int]
    SPARSE_RANK_FIELD_NUMBER: _ClassVar[int]
    chunk_id: str
    score: float
    content: str
    title: str
    page: int
    doc_id: str
    source: str
    extra: _containers.ScalarMap[str, str]
    dense_rank: int
    sparse_rank: int
    def __init__(
        self,
        chunk_id: _Optional[str] = ...,
        score: _Optional[float] = ...,
        content: _Optional[str] = ...,
        title: _Optional[str] = ...,
        page: _Optional[int] = ...,
        doc_id: _Optional[str] = ...,
        source: _Optional[str] = ...,
        extra: _Optional[_Mapping[str, str]] = ...,
        dense_rank: _Optional[int] = ...,
        sparse_rank: _Optional[int] = ...,
    ) -> None: ...

class SearchResponse(_message.Message):
    __slots__ = (
        "hits",
        "collection_used",
        "language_used",
        "user_has_no_documents",
        "total_user_chunks",
        "filters_applied",
        "degraded",
    )
    HITS_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_USED_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_USED_FIELD_NUMBER: _ClassVar[int]
    USER_HAS_NO_DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_USER_CHUNKS_FIELD_NUMBER: _ClassVar[int]
    FILTERS_APPLIED_FIELD_NUMBER: _ClassVar[int]
    DEGRADED_FIELD_NUMBER: _ClassVar[int]
    hits: _containers.RepeatedCompositeFieldContainer[Hit]
    collection_used: str
    language_used: str
    user_has_no_documents: bool
    total_user_chunks: int
    filters_applied: _containers.RepeatedScalarFieldContainer[str]
    degraded: bool
    def __init__(
        self,
        hits: _Optional[_Iterable[_Union[Hit, _Mapping]]] = ...,
        collection_used: _Optional[str] = ...,
        language_used: _Optional[str] = ...,
        user_has_no_documents: _Optional[bool] = ...,
        total_user_chunks: _Optional[int] = ...,
        filters_applied: _Optional[_Iterable[str]] = ...,
        degraded: _Optional[bool] = ...,
    ) -> None: ...

class ListTitlesRequest(_message.Message):
    __slots__ = ("user_id", "doc_ids", "limit")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DOC_IDS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    doc_ids: _containers.RepeatedScalarFieldContainer[str]
    limit: int
    def __init__(
        self,
        user_id: _Optional[str] = ...,
        doc_ids: _Optional[_Iterable[str]] = ...,
        limit: _Optional[int] = ...,
    ) -> None: ...

class TitleInfo(_message.Message):
    __slots__ = ("title", "chunk_count")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CHUNK_COUNT_FIELD_NUMBER: _ClassVar[int]
    title: str
    chunk_count: int
    def __init__(self, title: _Optional[str] = ..., chunk_count: _Optional[int] = ...) -> None: ...

class ListTitlesResponse(_message.Message):
    __slots__ = ("titles", "total_chunks", "truncated")
    TITLES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_CHUNKS_FIELD_NUMBER: _ClassVar[int]
    TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    titles: _containers.RepeatedCompositeFieldContainer[TitleInfo]
    total_chunks: int
    truncated: bool
    def __init__(
        self,
        titles: _Optional[_Iterable[_Union[TitleInfo, _Mapping]]] = ...,
        total_chunks: _Optional[int] = ...,
        truncated: _Optional[bool] = ...,
    ) -> None: ...

class EmbedRequest(_message.Message):
    __slots__ = ("texts", "purpose")
    TEXTS_FIELD_NUMBER: _ClassVar[int]
    PURPOSE_FIELD_NUMBER: _ClassVar[int]
    texts: _containers.RepeatedScalarFieldContainer[str]
    purpose: EmbedPurpose
    def __init__(
        self,
        texts: _Optional[_Iterable[str]] = ...,
        purpose: _Optional[_Union[EmbedPurpose, str]] = ...,
    ) -> None: ...

class DenseVector(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, values: _Optional[_Iterable[float]] = ...) -> None: ...

class SparseVector(_message.Message):
    __slots__ = ("indices", "values")
    INDICES_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    indices: _containers.RepeatedScalarFieldContainer[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(
        self, indices: _Optional[_Iterable[int]] = ..., values: _Optional[_Iterable[float]] = ...
    ) -> None: ...

class EmbedResponse(_message.Message):
    __slots__ = ("dense", "sparse", "model", "dimensions")
    DENSE_FIELD_NUMBER: _ClassVar[int]
    SPARSE_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    DIMENSIONS_FIELD_NUMBER: _ClassVar[int]
    dense: _containers.RepeatedCompositeFieldContainer[DenseVector]
    sparse: _containers.RepeatedCompositeFieldContainer[SparseVector]
    model: str
    dimensions: int
    def __init__(
        self,
        dense: _Optional[_Iterable[_Union[DenseVector, _Mapping]]] = ...,
        sparse: _Optional[_Iterable[_Union[SparseVector, _Mapping]]] = ...,
        model: _Optional[str] = ...,
        dimensions: _Optional[int] = ...,
    ) -> None: ...
