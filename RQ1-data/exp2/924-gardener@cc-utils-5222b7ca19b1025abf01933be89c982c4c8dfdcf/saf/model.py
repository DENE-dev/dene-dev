import dataclasses
import enum
import typing

import gci.componentmodel as cm

dc = dataclasses.dataclass

# generic evidence-model


@dc
class EvidenceMetadata:
    evidence_id: str
    collection_date: str


@dc
class EvidenceRequest:
    meta: EvidenceMetadata
    data: typing.Dict


# special-case evidence for gardener-mm5 (malware)


class MalwareScanState(enum.Enum):
    FINISHED_SUCCESSFULLY = 'finished_successfully'
    FINISHED_WITH_ERRORS = 'finished_with_errors'


@dc
class MalwarescanResult:
    component_name: str
    resource: cm.Resource
    scan_state: MalwareScanState
    findings: typing.List[str]


@dc
class MalwarescanEvidenceData:
    pipeline_url: str
    component_name: str
    scanning_endpoint: str
    scanning_cfg: str
    scan_results: typing.List[MalwareScanResult]


@dc
class MalwarescanEvidenceRequest(EvidenceRequest):
    data: MalwarescanEvidenceData