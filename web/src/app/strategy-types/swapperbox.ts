import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

interface SwapperBoxIndicator extends Indicator {
  signal: number[];
}

export class SwapperBoxStrategy extends Strategy {
  override indicators: SwapperBoxIndicator | null = null;
  url: string = '';
  telegram: string = '';
}
