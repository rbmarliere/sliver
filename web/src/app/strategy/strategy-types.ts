
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
  ];
}

export function getStrategyTypeName(value: number | null): string {
  const type = getStrategyTypes().find((strategyType) => strategyType.value === value);
  if (type) {
    // throw new Error(`Strategy type not found for value ${value}`);
    return type.name;
  }
  return '';
}
