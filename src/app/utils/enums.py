from enum import IntEnum


class NumberStatus(IntEnum):
    WAIT_CODE = 1
    CODE_RECEIVED = 2
    CANCELED = 3
    BANNED = 4
    WAIT_CODE_AGAIN = 5
    COMPLETED = 6
