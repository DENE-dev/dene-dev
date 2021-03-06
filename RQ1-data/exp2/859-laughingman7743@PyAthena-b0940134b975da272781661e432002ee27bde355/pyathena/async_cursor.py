# -*- coding: utf-8 -*-
import logging
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing import cpu_count
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from pyathena.common import CursorIterator
from pyathena.converter import Converter
from pyathena.cursor import BaseCursor
from pyathena.error import NotSupportedError, ProgrammingError
from pyathena.formatter import Formatter
from pyathena.result_set import AthenaResultSet
from pyathena.util import RetryConfig

if TYPE_CHECKING:
    from pyathena.connection import Connection

_logger = logging.getLogger(__name__)  # type: ignore


class AsyncCursor(BaseCursor):
    def __init__(
        self,
        connection: "Connection",
        s3_staging_dir: str,
        schema_name: str,
        work_group: str,
        poll_interval: float,
        encryption_option: str,
        kms_key: str,
        converter: Converter,
        formatter: Formatter,
        retry_config: RetryConfig,
        max_workers: int = (cpu_count() or 1) * 5,
        arraysize: int = CursorIterator.DEFAULT_FETCH_SIZE,
        kill_on_interrupt: bool = True,
    ) -> None:
        super(AsyncCursor, self).__init__(
            connection=connection,
            s3_staging_dir=s3_staging_dir,
            schema_name=schema_name,
            work_group=work_group,
            poll_interval=poll_interval,
            encryption_option=encryption_option,
            kms_key=kms_key,
            converter=converter,
            formatter=formatter,
            retry_config=retry_config,
            kill_on_interrupt=kill_on_interrupt,
        )
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._arraysize = arraysize

    @property
    def arraysize(self) -> int:
        return self._arraysize

    @arraysize.setter
    def arraysize(self, value: int) -> None:
        if value <= 0 or value > CursorIterator.DEFAULT_FETCH_SIZE:
            raise ProgrammingError(
                "MaxResults is more than maximum allowed length {0}.".format(
                    CursorIterator.DEFAULT_FETCH_SIZE
                )
            )
        self._arraysize = value

    def close(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait)

    def _description(self, query_id: str):
        result_set = self._collect_result_set(query_id)
        return result_set.description

    def description(self, query_id: str) -> Future:
        return self._executor.submit(self._description, query_id)

    def query_execution(self, query_id: str) -> Future:
        return self._executor.submit(self._get_query_execution, query_id)

    def poll(self, query_id: str) -> Future:
        return self._executor.submit(self._poll, query_id)

    def _collect_result_set(self, query_id: str) -> AthenaResultSet:
        query_execution = self._poll(query_id)
        return AthenaResultSet(
            connection=self._connection,
            converter=self._converter,
            query_execution=query_execution,
            arraysize=self._arraysize,
            retry_config=self._retry_config,
        )

    def execute(
        self,
        operation: str,
        parameters: Dict[str, Any] = None,
        work_group: Optional[str] = None,
        s3_staging_dir: Optional[str] = None,
        cache_size: int = 0,
    ) -> Tuple[str, Future]:
        query_id = self._execute(
            operation,
            parameters=parameters,
            work_group=work_group,
            s3_staging_dir=s3_staging_dir,
            cache_size=cache_size,
        )
        return query_id, self._executor.submit(self._collect_result_set, query_id)

    def executemany(self, operation: str, seq_of_parameters: List[Dict[str, Any]]):
        raise NotSupportedError

    def cancel(self, query_id: str) -> Future:
        return self._executor.submit(self._cancel, query_id)