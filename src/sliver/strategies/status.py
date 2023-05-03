import enum


class StrategyStatus(enum.IntEnum):
    INACTIVE = 0
    IDLE = 1
    RESETTING = 2
    REFRESHING = 3
    DELETED = 4

    @staticmethod
    def active():
        return [
            StrategyStatus.IDLE,
            StrategyStatus.RESETTING,
            StrategyStatus.REFRESHING,
        ]

    @staticmethod
    def refreshing():
        return [
            StrategyStatus.RESETTING,
            StrategyStatus.REFRESHING,
        ]
