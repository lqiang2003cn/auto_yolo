from auto_yolo import envs

readme = "Testing yolo_air."

distributions = None

durations = dict(
    long=dict(
        max_hosts=1, ppn=6, cpp=2, gpu_set="0,1", wall_time="24hours",
        project="rpp-bengioy", cleanup_time="20mins",
        slack_time="5mins", n_repeats=6, step_time_limit="24hours"),

    build=dict(
        max_hosts=1, ppn=1, cpp=2, gpu_set="0", wall_time="2hours",
        project="rpp-bengioy", cleanup_time="2mins",
        slack_time="2mins", n_repeats=1, step_time_limit="2hours",
        config=dict(do_train=False)),

    short=dict(
        max_hosts=1, ppn=2, cpp=2, gpu_set="0", wall_time="20mins",
        project="rpp-bengioy", cleanup_time="1mins",
        slack_time="1mins", n_repeats=1, n_param_settings=4),
)

config = dict(
    n_train=16000,
    background_cfg=dict(mode="colour", colour="white"),
    shapes="black,circle blue,circle green,square",
    image_shape=(36, 36),
    obj_logit_scale=1.0,
    alpha_logit_scale=1.0,
    alpha_logit_bias=1.0,
)

envs.run_experiment(
    "test", config, readme, alg="yolo_air",
    task="shapes", durations=durations, distributions=distributions,
)
