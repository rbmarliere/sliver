
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
  ];
}

