
export interface StrategyType {
  value: number;
  name: string;
}

export function getStrategyTypes(): StrategyType[] {
  return [
    {
      value: 0,
      name: 'MANUAL',
    },
    {
      value: 1,
      name: 'RANDOM',
    },
    {
      value: 2,
      name: 'HYPNOX',
    },
    {
      value: 3,
      name: 'DD3',
    },
    {
      value: 4,
      name: 'MIXER',
    },
    {
      value: 5,
      name: 'BB',
    },
    {
      value: 6,
      name: 'MA_CROSS',
    },
    {
      value: 7,
      name: 'SWAPPERBOX',
    }
  ];
}

export function getStrategyTypeName(value: number | null): string {
  const type = getStrategyTypes().find((strategyType) => strategyType.value === value);

  if (type)
    return type.name;

  return '';
}
