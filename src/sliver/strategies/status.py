import enum


class StrategyStatus(enum.IntEnum):
    INACTIVE = 0
    IDLE = 1
    IDLE_RESET = 2
    REFRESHING = 3
    DELETED = 4
    RESETTING = 5

    @staticmethod
    def active():
        return [
            StrategyStatus.IDLE,
            StrategyStatus.IDLE_RESET,
            StrategyStatus.RESETTING,
            StrategyStatus.REFRESHING,
        ]

    @staticmethod
    def refreshing():
        return [
            StrategyStatus.RESETTING,
            StrategyStatus.REFRESHING,
        ]
