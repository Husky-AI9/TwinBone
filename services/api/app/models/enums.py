"""Shared constrained values mirrored by CockroachDB CHECK constraints."""

from enum import StrEnum


class UserRole(StrEnum):
    PATIENT = "PATIENT"
    CLINICIAN = "CLINICIAN"
    RESEARCHER = "RESEARCHER"
    ADMIN = "ADMIN"
    JUDGE = "JUDGE"


class MemoryType(StrEnum):
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    TASK = "TASK"
    EVIDENCE = "EVIDENCE"


class VerificationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"


class ActorType(StrEnum):
    USER = "USER"
    CLINICIAN = "CLINICIAN"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
    RESEARCHER = "RESEARCHER"
