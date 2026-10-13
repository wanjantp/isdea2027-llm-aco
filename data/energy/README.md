# UAV parameters: DJI Agras T25 (derived)

Airframe: DJI Agras T25 (20 L spray tank), the small-field model sold in Thailand by Siam Kubota (2024-).
Source A: DJI Agras T25 specifications, https://ag.dji.com/t25/specs (accessed 2026-10-13):
  weight 25.4 kg (no battery) / 32 kg (with battery); max take-off weight 52 kg (spraying); spray width 4-7 m at 3 m height;
  DB800 battery 15,500 mAh x 52.22 V = 809 Wh = 2.91 MJ; obstacle-avoidance speed limit 10 m/s; charge 9-12 min.
Source B: DJI Agras T20P specifications, https://ag.dji.com/t20p/specs (same airframe class: 32 kg / 52 kg):
  hover time 14.5 min at 32 kg (13,000 mAh x 52.22 V = 679 Wh -> 2.81 kW) and 7 min at 52 kg (-> 5.82 kW).
DJI does not publish power or endurance for the T25, so power is interpolated from Source B:
  P_work = P_hover = 4.3 kW (mid-mission, ~42 kg), P_transit = 3.5 kW (lighter, forward flight), v_work = 5 m/s, v_transit = 10 m/s.
Turn cost: c_turn = 1.5 kJ per 180 deg U-turn plus hover power during the turn at 90 deg/s (sensitivity x0.5, x2 in the paper).
Reserve 15 %. Sortie overhead 60 kJ / 180 s (take-off, landing, battery swap).
Previous placeholder (used for tuning and the first evolution runs): P_work 3500, P_transit 3000, P_hover 3200, E_battery 2.8e6.
