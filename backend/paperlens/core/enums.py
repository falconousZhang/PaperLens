from enum import StrEnum


class PaperStatus(StrEnum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    PARSED = "PARSED"
    FAILED = "FAILED"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskType(StrEnum):
    REVIEW = "REVIEW"
    METRIC_EXTRACTION = "METRIC_EXTRACTION"
    EXPERIMENT_ANALYSIS = "EXPERIMENT_ANALYSIS"


class SectionType(StrEnum):
    ABSTRACT = "ABSTRACT"
    INTRODUCTION = "INTRODUCTION"
    METHOD = "METHOD"
    EXPERIMENT = "EXPERIMENT"
    RESULT = "RESULT"
    DISCUSSION = "DISCUSSION"
    CONCLUSION = "CONCLUSION"
    REFERENCES = "REFERENCES"
    APPENDIX = "APPENDIX"
    OTHER = "OTHER"


class EvidenceType(StrEnum):
    TEXT = "TEXT"
    TABLE = "TABLE"
    FIGURE_CAPTION = "FIGURE_CAPTION"
    EQUATION = "EQUATION"


class FindingType(StrEnum):
    STRENGTH = "STRENGTH"
    WEAKNESS = "WEAKNESS"
    SUGGESTION = "SUGGESTION"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"


class ExportStatus(StrEnum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class CheckpointType(StrEnum):
    FINAL = "FINAL"
    MAX = "MAX"
    MEAN = "MEAN"
    BEST = "BEST"
    LAST = "LAST"
    UNKNOWN = "UNKNOWN"


class ReviewDimension(StrEnum):
    SOUNDNESS = "SOUNDNESS"
    NOVELTY = "NOVELTY"
    CLARITY = "CLARITY"
    COMPLETENESS = "COMPLETENESS"
    REPRODUCIBILITY = "REPRODUCIBILITY"
    SIGNIFICANCE = "SIGNIFICANCE"
    OVERALL = "OVERALL"


class OverallVerdict(StrEnum):
    ACCEPT = "ACCEPT"
    WEAK_ACCEPT = "WEAK_ACCEPT"
    BORDERLINE = "BORDERLINE"
    WEAK_REJECT = "WEAK_REJECT"
    REJECT = "REJECT"


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class ExperimentFileType(StrEnum):
    CSV = "CSV"
    XLSX = "XLSX"
    XLS = "XLS"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class LearningMode(StrEnum):
    SUMMARY = "SUMMARY"
    EXPLAIN = "EXPLAIN"
    TRANSLATE = "TRANSLATE"


class LearningScopeType(StrEnum):
    SECTION = "SECTION"
    PAGE = "PAGE"
    EVIDENCE = "EVIDENCE"


class LearningStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class QATurnStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ReadingStatus(StrEnum):
    TO_READ = "TO_READ"
    READING = "READING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class HighlightColor(StrEnum):
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    BLUE = "BLUE"
    PINK = "PINK"


class AnchorType(StrEnum):
    PAPER = "PAPER"
    PAGE = "PAGE"
    HIGHLIGHT = "HIGHLIGHT"


class MasteryStatus(StrEnum):
    NEW = "NEW"
    LEARNING = "LEARNING"
    MASTERED = "MASTERED"