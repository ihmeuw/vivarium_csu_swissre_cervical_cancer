from vivarium_csu_swissre_cervical_cancer.utilities import TruncnormDist
from vivarium_csu_swissre_cervical_cancer import data_keys

REMISSION_RATE = 0.1
HRHPV_INCIDENCE = 0.01  # TODO: this is a made-up number, need real value
HRHPV_REMISSION_RATE = 0.3  # TODO: replace this SWAG

# TODO: change this to taking in a CSV of table values
BCC_PREVALENCE_RATIO = TruncnormDist(
    data_keys.CERVICAL_CANCER.BCC_PREVALENCE_RATIO, 0.07, 0.06, 0.0, 100.0)

# BCC duration: "temporarily use 14.5 years"
BCC_DURATION = 14.5

# Inferred from: the infection rate of high-risk HPVs in women aged <25, 25-45, and >45 years
# was 24.3% (95%CI, 19.0%-29.6%), 19.9% (95%CI, 16.4-23.4), and 21.4% (95%CI, 17.3-25.5), respectively.
PREV_DISTS_HPV = {
    "<25": TruncnormDist("hrHPV prevalence age < 25", 0.243, 0.0265),
    "25-45": TruncnormDist("hrHPV prevalence 25 <= age <= 45", 0.199, 0.0175),
    ">45": TruncnormDist("hrHPV prevalence age > 45", 0.214, 0.0205)
}

# use numpy normal get random variable
# from: https://vivarium-research.readthedocs.io/en/latest/gbd2017_models/causes/neoplasms/cervical_cancer/cervical_cancer_cause_model.html?highlight=cervical%20cancer
# relative risk of developing BCC for hrHPV infected women versus without HPV infection = 16.2 (95%CI 9.6 to 27.3)
# mean, stddev, key
#Lets start with log-normal, since the CI is so asymmetric
RR_HRHPV_PARAMS = (16.2, 4.425, "rr_hrhpv_dist")