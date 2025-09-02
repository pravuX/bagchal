# eat_max = 4
# trap_max = 3
# goat_presence_max = 20
# inaccessible_max = 10
# potential_capture_max = 11
#
# w_eat = 1.5
# w_potcap = 1.5
#
# w_trap = 1.5
# w_presence = 0.9
# w_inacc = 0.6
#
#
# # all max
# raw = (eat_max / eat_max) * w_eat
# raw -= (trap_max / trap_max) * w_trap
# raw -= (goat_presence_max / goat_presence_max) * w_presence
# raw -= (inaccessible_max / inaccessible_max) * w_inacc
# raw += (potential_capture_max / potential_capture_max) * w_potcap
# print(raw)  # 0.0
#
# # tiger best
# raw = (eat_max / eat_max) * w_eat
# raw -= (0 / trap_max) * w_trap
# raw -= (0 / goat_presence_max) * w_presence
# raw -= (0 / inaccessible_max) * w_inacc
# raw += (potential_capture_max / potential_capture_max) * w_potcap
# print(raw)  # 3.0
#
# # goat best
# raw = (0 / eat_max) * w_eat
# raw -= (trap_max / trap_max) * w_trap
# raw -= (goat_presence_max / goat_presence_max) * w_presence
# raw -= (inaccessible_max / inaccessible_max) * w_inacc
# raw += (0 / potential_capture_max) * w_potcap
# print(raw)  # -3.0
