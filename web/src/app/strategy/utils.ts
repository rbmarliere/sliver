export function msToString(ms: number): string {
  // https://stackoverflow.com/questions/29816872/how-can-i-convert-milliseconds-to-hhmmss-format-using-javascript
  var seconds = ms / 1000;
  const days = parseInt((seconds / 86400).toString());
  seconds = seconds % 86400;
  const hours = parseInt((seconds / 3600).toString());
  seconds = seconds % 3600;
  const minutes = parseInt((seconds / 60).toString());
  return `${days}d ${hours}h ${minutes}m`;
}

export function median(values: any): any {
  // https://stackoverflow.com/questions/45309447/calculating-median-javascript
  if (values.length === 0) return 0;
  if (containsNaN(values)) return 0;

  values.sort(function(a: number, b: number) {
    return a - b;
  });

  var half = Math.floor(values.length / 2);

  if (values.length % 2) return values[half];

  return (values[half - 1] + values[half]) / 2.0;
}

export function mean(values: any): any {
  if (values.length === 0) return 0;
  if (containsNaN(values)) return 0;

  const sum = values.reduce((a: any, b: any) => a + b, 0);
  const avg = sum / values.length || 0;
  return avg;
}

// function that checks if a list contains a NaN value
export function containsNaN(values: any): boolean {
  for (var i = 0; i < values.length; i++) {
    if (isNaN(values[i])) {
      return true;
    }
  }
  return false;
}
