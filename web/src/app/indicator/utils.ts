export function msToString(ms: number): string {
  var seconds = ms / 1000;
  const days = parseInt((seconds / 86400).toString());
  seconds = seconds % 86400;
  const hours = parseInt((seconds / 3600).toString());
  seconds = seconds % 3600;
  const minutes = parseInt((seconds / 60).toString());
  return `${days}d ${hours}h ${minutes}m`;
}

export function median(_values: number[]): number {
  let values = [..._values]; // copy first, since sort() is in-place

  if (values.length === 0)
    return 0;

  values.sort(function(a: number, b: number) {
    return a - b;
  });

  var half = Math.floor(values.length / 2);

  if (values.length % 2)
    return values[half];

  return (values[half - 1] + values[half]) / 2.0;
}

export function mean(values: number[]): number {
  if (values.length === 0)
    return 0;

  const sum = values.reduce((a: number, b: number) => a + b, 0);
  const avg = sum / values.length || 0;
  return avg;
}

export function variance(values: number[]): number {
  if (values.length === 0)
    return 0;

  const avg = mean(values);
  const squareDiffs = values.map(function(value: number) {
    var diff = value - avg;
    var sqrDiff = diff * diff;
    return sqrDiff;
  });

  const avgSquareDiff = mean(squareDiffs);
  return avgSquareDiff;
}
