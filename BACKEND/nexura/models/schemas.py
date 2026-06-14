from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ToolType(str, Enum):
    NMAP = "nmap"
    NUCLEI = "nuclei"
    NIKTO = "nikto"
    SQLMAP = "sqlmap"
    GOBUSTER = "gobuster"
    AMASS = "amass"
    NETWORK = "network"
    WHATWEB = "whatweb"


class ScanTarget(BaseModel):
    target: str
    description: str | None = None


class ToolCommand(BaseModel):
    tool: ToolType
    args: list[str]
    description: str


class ScanPlan(BaseModel):
    target: str
    intent: str
    tools: list[ToolCommand] = Field(default_factory=list)
    reasoning: str = ""
    agentic: bool = False


class PortInfo(BaseModel):
    port: int = Field(ge=1, le=65535, description="Valid port (1-65535)")
    state: str
    service: str | None = None
    version: str | None = None

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be 1-65535, got {v}")
        return v


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    UNKNOWN = "UNKNOWN"


class Vulnerability(BaseModel):
    name: str
    severity: str
    description: str | None = None
    url: str | None = None
    cve: str | None = None
    cvss: float | None = Field(None, ge=0.0, le=10.0)
    solution: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"}
        if v.upper() not in valid:
            raise ValueError(f"Severity must be one of {valid}, got {v}")
        return v.upper()

    @field_validator("cvss")
    @classmethod
    def validate_cvss(cls, v):
        if v is not None and not (0.0 <= v <= 10.0):
            raise ValueError(f"CVSS must be 0-10, got {v}")
        return v


class ScanResult(BaseModel):
    tool: str
    target: str
    start_time: datetime
    end_time: datetime | None = None
    success: bool
    raw_output: str | None = None
    error: str | None = None
    ports: list[PortInfo] = Field(default_factory=list)
    vulnerabilities: list[Vulnerability] = Field(default_factory=list)
    summary: str | None = None


class ParserResult(BaseModel):
    ports: list[PortInfo] = Field(default_factory=list)
    vulnerabilities: list[Vulnerability] = Field(default_factory=list)
    summary: str | None = None


class ScanReport(BaseModel):
    id: str
    target: str
    intent: str
    start_time: datetime
    end_time: datetime | None = None
    status: str = "running"
    results: list[ScanResult] = Field(default_factory=list)
    html_path: str | None = None
    technologies: dict | None = None
