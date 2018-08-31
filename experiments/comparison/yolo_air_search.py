import argparse

from auto_yolo import envs
from auto_yolo.models import yolo_air

readme = "Running YOLO AIR experiment."

distributions = dict(
    kernel_size=[1, 2, 3],  # 3 doesn't work well
    final_count_prior_log_odds=[0.1, 0.05, 0.025, 0.0125],
    hw_prior_std=[0.5, 1.0, 2.0],  # Anything outside of these bounds doesn't work very well.
    count_prior_decay_steps=[1000, 2000, 3000, 4000],
)


durations = dict(
    long=dict(
        max_hosts=1, ppn=16, cpp=1, gpu_set="0,1,2,3", wall_time="36hours",
        project="rpp-bengioy", cleanup_time="10mins",
        slack_time="10mins", n_repeats=6, step_time_limit="36hours"),

    build=dict(
        max_hosts=1, ppn=1, cpp=2, gpu_set="0", wall_time="20mins",
        project="rpp-bengioy", cleanup_time="2mins",
        slack_time="2mins", n_repeats=1, step_time_limit="20mins",
        config=dict(do_train=False)),

    short=dict(
        max_hosts=1, ppn=3, cpp=2, gpu_set="0", wall_time="30mins",
        project="rpp-bengioy", cleanup_time="2mins",
        slack_time="2mins", n_repeats=1, config=dict(max_steps=100))
)

config = dict(
    curriculum=[dict()],
    n_train=64000, stopping_criteria="AP,max", threshold=0.99, patience=50000,
    render_hook=yolo_air.YoloAir_ComparisonRenderHook(show_zero_boxes=False),
    n_digits=9, min_digits=9, max_digits=9, max_steps=2e5,
    background_cfg=dict(mode="learn_solid"),
    train_example_range=(0.0, 0.7),
    val_example_range=(0.7, 0.8),
    test_example_range=(0.8, 0.9),
)

parser = argparse.ArgumentParser()
parser.add_argument("--no-lookback", action="store_true")
args, _ = parser.parse_known_args()

if args.no_lookback:
    config["sequential_cfg:n_lookback"] = 0

envs.run_experiment(
    "yolo_air_search_n_digits=9", config, readme, distributions=distributions,
    alg="yolo_air", task="arithmetic", durations=durations,
)
