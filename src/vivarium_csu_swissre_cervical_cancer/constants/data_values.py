from typing import NamedTuple

from vivarium_csu_swissre_cervical_cancer.utilities import TruncnormDist

REMISSION_RATE = 0.1

# BCC duration: "temporarily use 14.5 years"
BCC_DURATION = 14.5

# use numpy normal get random variable
# from: https://vivarium-research.readthedocs.io/en/latest/gbd2017_models/causes/neoplasms/cervical_cancer/
#   cervical_cancer_cause_model.html?highlight=cervical%20cancer
# relative risk of developing BCC for hrHPV infected women versus without HPV infection = 16.2 (95%CI 9.6 to 27.3)
# mean, stddev, key
# Lets start with log-normal, since the CI is so asymmetric - Abie
RR_HRHPV_PARAMS = (16.2, 4.425, "rr_hrhpv_dist")

DAYS_UNTIL_NEXT_ANNUAL = TruncnormDist('days_until_next_annual', 395.0, 72.0, 180.0, 1800.0)
DAYS_UNTIL_NEXT_TRIENNIAL = (1185.0, 72.0)
DAYS_UNTIL_NEXT_QUINQUENNIAL = (1975.0, 72.0)


###########################################
# Screening and Treatment Model Constants #
###########################################

PROBABILITY_ATTENDING_SCREENING_KEY = 'probability_attending_screening'
PROBABILITY_ATTENDING_FIRST_SCREENING_MEAN = 0.25
PROBABILITY_ATTENDING_FIRST_SCREENING_STDDEV = 0.0025
# 1.89 with 95%CI 1.06-2.49 (Yan et al. 2017)
# stddev = (2.49-1.06)/4 = .35750000000000000000
ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_KEY = 'attended_previous_screening_multiplier'
ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_MEAN = 1.89
ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_STDDEV = 0.3575
# PROBABILITY_ATTENDING_GIVEN_PREVIOUS_NO_ATTENDANCE derivation
# p = prob attends screening
# p1 = prob attends screening given attended previous
# p2 = prob attends screening given didn't attend previous
# n = total population
# n1 = population who attended previous screening
# n2 = population who didn't
# m = multiplier ~ 1.89
# p ~ 0.25
# p1 = m * p2
# p = p1 * p + p2 * (1-p)
# p2 = p1/m

ATTENDED_LAST_SCREENING = 'attended_last_screening'
PREVIOUS_SCREENING_DATE = 'previous_screening_date'
NEXT_SCREENING_DATE = 'next_screening_date'

FIRST_SCREENING_AGE = 21
MID_SCREENING_AGE = 30
LAST_SCREENING_AGE = 65


class __Screening(NamedTuple):
    # TODO: need stddev for COTEST_CC_SENSITIVITY
    COTEST_CC_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_cc_sensitivity', 0.591, 0.0)
    COTEST_CC_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_cc_specificity', 1.0, 0.0)

    # TODO: need stddev for COTEST_HPV_SENSITIVITY, info for COTEST_HPV_SPECIFICITY (assuming 100% for now)
    COTEST_HPV_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 0.767, 0.0)
    COTEST_HPV_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_hpv_specificity', 0.941, 0.0)

    # CYTOLOGY_SENSITIVITY ~ 65.9% (95% CI 54.9 to 75.3)
    CYTOLOGY_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 0.659, 0.051)
    CYTOLOGY_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 1.0, 0.0)

    REMISSION_SENSITIVITY: TruncnormDist = TruncnormDist('remission_sensitivity', 1.0, 0.0)
    REMISSION_SPECIFICITY: TruncnormDist = TruncnormDist('remission_specificity', 1.0, 0.0)

    BASE_ATTENDANCE: TruncnormDist = TruncnormDist('start_attendance_base',
                                                   PROBABILITY_ATTENDING_FIRST_SCREENING_MEAN,
                                                   PROBABILITY_ATTENDING_FIRST_SCREENING_STDDEV,
                                                   key=PROBABILITY_ATTENDING_SCREENING_KEY)
    # XXX: does this need to be a distribution? If so, Truncnorm bounds should be what?? (1, 2+)
    ATTENDED_PREVIOUS_SCREENING_MULTIPLIER: TruncnormDist = TruncnormDist('attended_prev_screening_multiplier',
                                                                          ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_MEAN,
                                                                          ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_STDDEV,
                                                                          1,
                                                                          ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_MEAN*3,
                                                                          key=ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_KEY
                                                                          )

    # START_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('start_attendance_attended_prev', 0.397, 0.00397,
    #                                                               key=PROBABILITY_ATTENDING_SCREENING_KEY)
    # START_NOT_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('start_attendance_not_attended_prev', 0.258,
    #                                                                   0.00258, key=PROBABILITY_ATTENDING_SCREENING_KEY)
    # END_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('end_attendance_attended_prev', 0.782, 0.00782,
    #                                                             key=PROBABILITY_ATTENDING_SCREENING_KEY)
    # END_NOT_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('end_attendance_not_attended_prev', 0.655, 0.00655,
    #                                                                 key=PROBABILITY_ATTENDING_SCREENING_KEY)

    @property
    def name(self):
        return 'screening_result'

    @property
    def log_name(self):
        return 'screening result'


SCREENING = __Screening()
