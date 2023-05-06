import enum


class StrategyStatus(enum.IntEnum):
    DELETED = 0
    INACTIVE = 1
    IDLE = 2
    FETCHING = 3
    WAITING = 4
    REFRESHING = 5

    @staticmethod
    def active():
        return [
            StrategyStatus.IDLE,
            StrategyStatus.FETCHING,
            StrategyStatus.WAITING,
            StrategyStatus.REFRESHING,
        ]

    @staticmethod
    def refreshing():
        return [
            StrategyStatus.FETCHING,
            StrategyStatus.WAITING,
            StrategyStatus.REFRESHING,
        ]
