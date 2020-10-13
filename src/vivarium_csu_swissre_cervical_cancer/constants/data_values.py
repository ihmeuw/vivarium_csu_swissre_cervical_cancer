
REMISSION_RATE = 0.1
HRHPV_INCIDENCE = 0.01  # TODO: this is a made-up number, need real value
HRHPV_REMISSION_RATE = 0.3  # TODO: replace this SWAG

# BCC duration: "temporarily use 14.5 years"
BCC_DURATION = 14.5

# use numpy normal get random variable
# from: https://vivarium-research.readthedocs.io/en/latest/gbd2017_models/causes/neoplasms/cervical_cancer/
#   cervical_cancer_cause_model.html?highlight=cervical%20cancer
# relative risk of developing BCC for hrHPV infected women versus without HPV infection = 16.2 (95%CI 9.6 to 27.3)
# mean, stddev, key
# Lets start with log-normal, since the CI is so asymmetric - Abie
RR_HRHPV_PARAMS = (16.2, 4.425, "rr_hrhpv_dist")
