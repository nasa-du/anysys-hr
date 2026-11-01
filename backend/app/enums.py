from enum import StrEnum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    PROBATION = "probation"
    RESIGNED = "resigned"


class ContractType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    INTERN = "intern"
    LABOR = "labor"
