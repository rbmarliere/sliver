import { Strategy } from "../strategy";
import { BBStrategy } from "./bb";
import { DD3Strategy } from "./dd3";
import { ElNinoStrategy } from "./elnino";
import { HypnoxStrategy } from "./hypnox";
import { Hypnoxv2Strategy } from "./hypnoxv2";
import { LaNinaStrategy } from "./lanina";
import { ManualStrategy } from "./manual";
import { MACrossStrategy } from "./ma_cross";
import { MixerStrategy } from "./mixer";
import { RandomStrategy } from "./random";
import { SwapperBoxStrategy } from "./swapperbox";
import { WindrunnerStrategy } from "./windrunner";

export enum StrategyType {
  MANUAL = 0,
  RANDOM = 1,
  HYPNOX = 2,
  DD3 = 3,
  MIXER = 4,
  BB = 5,
  MA_CROSS = 6,
  SWAPPERBOX = 7,
  WINDRUNNER = 8,
  HYPNOXV2 = 9,
  ELNINO = 10,
  LANINA = 11,
}

export function StrategyFactory(base: Strategy): Strategy {
  switch (base.type) {
    case StrategyType.MANUAL:
      return ManualStrategy.fromData(base);
    case StrategyType.RANDOM:
      return RandomStrategy.fromData(base);
    case StrategyType.HYPNOX:
      return HypnoxStrategy.fromData(base);
    case StrategyType.DD3:
      return DD3Strategy.fromData(base);
    case StrategyType.MIXER:
      return MixerStrategy.fromData(base);
    case StrategyType.BB:
      return BBStrategy.fromData(base);
    case StrategyType.MA_CROSS:
      return MACrossStrategy.fromData(base);
    case StrategyType.SWAPPERBOX:
      return SwapperBoxStrategy.fromData(base);
    case StrategyType.WINDRUNNER:
      return WindrunnerStrategy.fromData(base);
    case StrategyType.HYPNOXV2:
      return Hypnoxv2Strategy.fromData(base);
    case StrategyType.ELNINO:
      return ElNinoStrategy.fromData(base);
    case StrategyType.LANINA:
      return LaNinaStrategy.fromData(base);
    default:
      return base;
  }
}
