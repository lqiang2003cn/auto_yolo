import numpy as np
import tensorflow as tf
import copy

from dps.utils import Config
from dps.utils.tf import MLP

from auto_yolo.models import core, air, yolo_rl, yolo_air, yolo_math, yolo_xo


alg_config = Config(
    get_updater=core.Updater,

    batch_size=32,
    lr_schedule=1e-4,
    optimizer_spec="adam",
    max_grad_norm=1.0,
    use_gpu=True,
    gpu_allow_growth=True,
    eval_mode="val",
    max_experiments=None,
    preserve_env=True,
    stopping_criteria="loss,min",
    threshold=-np.inf,

    curriculum=[
        dict(),
    ],
)


yolo_rl_config = alg_config.copy(
    alg_name="yolo_rl",
    build_network=yolo_rl.YoloRL_Network,

    stopping_criteria="TOTAL_COST,min",

    render_hook=yolo_rl.YoloRL_RenderHook(),

    # model params

    build_backbone=core.Backbone,
    build_next_step=core.NextStep,
    build_object_encoder=lambda scope: MLP([100, 100], scope=scope),
    build_object_decoder=lambda scope: MLP([100, 100], scope=scope),

    # build_object_decoder=core.ObjectDecoder,

    use_input_attention=False,
    decoder_logit_scale=10.0,

    max_object_shape=(28, 28),
    pixels_per_cell=(8, 8),
    anchor_boxes=[[14, 14]],

    kernel_size=(3, 3),

    n_channels=128,
    n_decoder_channels=128,
    A=100,
    n_passthrough_features=0,
    n_backbone_features=100,

    min_hw=0.0,
    max_hw=3.0,

    box_std=0.0,
    attr_std=0.0,
    z_std=0.1,
    obj_exploration=0.05,
    obj_default=0.5,
    explore_during_val=False,

    use_baseline=True,

    # Costs
    area_weight=1.0,
    nonzero_weight=25.0,
    rl_weight=1.0,
    hw_weight=None,
    z_weight=None,

    area_neighbourhood_size=2,
    hw_neighbourhood_size=None,
    nonzero_neighbourhood_size=2,
    local_reconstruction_cost=True,

    target_area=0.0,
    target_hw=0.0,

    fixed_values=dict(),
    fixed_weights="",
    order="box obj z attr",

    sequential_cfg=dict(
        on=True,
        lookback_shape=(2, 2, 2),
        build_next_step=lambda scope: MLP([100, 100], scope=scope),
    ),
)

air_config = Config(
    alg_name="attend_infer_repeat",
    build_network=air.AIR_Network,

    batch_size=64,

    verbose_summaries=False,

    render_hook=air.AIR_RenderHook(),

    # model params - based on the values in tf-attend-infer-repeat/training.py
    max_time_steps=3,
    rnn_units=256,
    object_shape=(14, 14),
    vae_latent_dimensions=50,
    vae_recognition_units=(512, 256),
    vae_generative_units=(256, 512),
    scale_prior_mean=-1.0,
    scale_prior_variance=0.05,
    shift_prior_mean=0.0,
    shift_prior_variance=1.0,
    vae_prior_mean=0.0,
    vae_prior_variance=1.0,
    vae_likelihood_std=0.3,
    scale_hidden_units=64,
    shift_hidden_units=64,
    z_pres_hidden_units=64,
    z_pres_prior_log_odds="Exponential(start=10000.0, end=0.000000001, decay_rate=0.1, decay_steps=3000, log=True)",
    z_pres_temperature=1.0,
    stopping_threshold=0.99,
    cnn=False,
    cnn_filters=128,
    per_process_gpu_memory_fraction=0.3,
)


def yolo_air_prepare_func():
    from dps import cfg
    if cfg.postprocessing:
        cfg.anchor_boxes = [cfg.tile_shape]
    else:
        cfg.anchor_boxes = [cfg.image_shape]

    cfg.count_prior_log_odds = (
        "Exp(start=10000.0, end={}, decay_rate=0.1, "
        "decay_steps={}, log=True)".format(
            cfg.final_count_prior_log_odds, cfg.count_prior_decay_steps)
    )
    cfg.kernel_size = (cfg.kernel_size, cfg.kernel_size)


yolo_air_config = alg_config.copy(
    alg_name="yolo_air",
    build_network=yolo_air.YoloAir_Network,
    prepare_func=yolo_air_prepare_func,

    stopping_criteria="mAP,max",
    threshold=1.0,

    render_hook=yolo_air.YoloAir_RenderHook(),

    build_backbone=core.Backbone,
    build_next_step=core.NextStep,
    build_object_encoder=lambda scope: MLP([512, 256], scope=scope),
    build_object_decoder=lambda scope: MLP([256, 512], scope=scope),

    pixels_per_cell=(12, 12),

    n_channels=128,
    n_decoder_channels=128,
    A=50,

    sequential_cfg=dict(
        on=True,
        lookback_shape=(2, 2, 2),
        build_next_step=lambda scope: MLP([100, 100], scope=scope),
    ),

    use_concrete_kl=False,
    n_final_layers=3,
    object_shape=(14, 14),

    min_yx=-0.5,
    max_yx=1.5,

    hw_prior_mean=np.log(0.1/0.9),

    # Found through hyper parameter search
    hw_prior_std=0.5,
    count_prior_decay_steps=1000,
    final_count_prior_log_odds=0.0125,
    kernel_size=1,

    curriculum=[
        dict(postprocessing="random", tile_shape=(40, 40), n_samples_per_image=4),
        dict(do_train=False, n_train=16, min_chars=1, preserve_env=False),
    ],
)

# --- MATH ---

yolo_math_config = yolo_air_config.copy(
    alg_name="yolo_math",
    build_network=yolo_math.YoloAir_MathNetwork,
    stopping_criteria="math_accuracy,max",
    threshold=1.0,

    build_math_network=yolo_math.SequentialRegressionNetwork,
    build_math_cell=lambda scope: tf.contrib.rnn.LSTMBlockCell(128),
    build_math_output=lambda scope: MLP([100, 100], scope=scope),
    build_math_input=lambda scope: MLP([100, 100], scope=scope),

    math_weight=5.0,
    train_kl=True,
    train_reconstruction=True,
    noise_schedule=0.001,

    curriculum=[dict()],
)

curriculum_2stage = [
    dict(
        max_steps=30000,
        stopping_criteria="loss_reconstruction,min",
        threshold=0.0,
        math_weight=0.0,
        train_reconstruction=True,
        fixed_weights="math",

        postprocessing="random",
        tile_shape=(48, 48),
        n_samples_per_image=4,
    ),
    dict(
        render_step=10000,
        max_steps=100000000,
        preserve_env=False,
        math_weight=1.0,
        train_reconstruction=False,
        train_kl=False,
        fixed_weights="object_encoder object_decoder box obj backbone edge",
    )
]

yolo_math_2stage_config = yolo_math_config.copy(
    alg_name="yolo_math_2stage",
    curriculum=curriculum_2stage,
)

# --- SIMPLE_MATH ---

yolo_math_simple_config = yolo_math_config.copy(
    alg_name="simple_math",
    build_network=yolo_math.SimpleMathNetwork,
    render_hook=yolo_math.SimpleMath_RenderHook(),
    build_math_encoder=core.Backbone,
    build_math_decoder=core.InverseBackbone,
    train_reconstruction=False,
    train_kl=False,
    variational=False,
)

curriculum_simple_2stage = copy.deepcopy(curriculum_2stage)
curriculum_simple_2stage[0]['postprocessing'] = ""

yolo_math_simple_2stage_config = yolo_math_simple_config.copy(
    alg_name="simple_math_2stage",
    curriculum=curriculum_simple_2stage,
)

# --- XO ---

yolo_xo_config = yolo_math_config.copy(
    alg_name="yolo_xo",
    build_network=yolo_xo.YoloAIR_XONetwork,
    build_math_network=yolo_math.AttentionRegressionNetwork,
)

yolo_xo_2stage_config = yolo_xo_config.copy(
    alg_name="yolo_xo_2stage",
    curriculum=curriculum_2stage,
)

yolo_xo_init_config = yolo_xo_config.copy(
    alg_name="yolo_xo_init",
    keep_prob=0.25,
    balanced=False,
    n_train=60000,
    n_samples_per_image=1,
    curriculum=[dict()],
)

yolo_xo_init_config.update(curriculum_2stage[0])
yolo_xo_init_config.max_steps = 100000
yolo_xo_init_config.patience = 5000


yolo_xo_continue_config = yolo_xo_config.copy(
    alg_name="yolo_xo_continue",
    balanced=True,
    n_train=1000,
    n_samples_per_image=1,
    curriculum=[dict()],
    load_path={
        "YoloAIR_XONetwork/reconstruction":
            "/media/data/dps_data/logs/local_run_env=xo/exp_alg=yolo_xo_init_seed=525580444_2018_06_04_05_28_03/weights/best_of_stage_0"
    },
    build_math_network=lambda scope: MLP([100, 100, 100], scope=scope),
)

yolo_xo_continue_config.update(curriculum_2stage[1])
yolo_xo_continue_config.max_steps = 100000
yolo_xo_continue_config.patience = 5000


# --- SIMPLE_XO ---

yolo_xo_simple_config = yolo_math_simple_config.copy(
    alg_name="simple_xo",
    build_network=yolo_xo.SimpleXONetwork,
    build_math_network=yolo_math.AttentionRegressionNetwork,
)

yolo_xo_simple_2stage_config = yolo_xo_simple_config.copy(
    alg_name="simple_xo_2stage",
    curriculum=curriculum_simple_2stage
)

yolo_xo_simple_init_config = yolo_xo_simple_config.copy(
    alg_name="yolo_xo_simple_init",
    keep_prob=0.25,
    balanced=False,
    n_train=60000,
    n_samples_per_image=1,
    curriculum=[dict()],
)

yolo_xo_simple_init_config.update(curriculum_simple_2stage[0])
yolo_xo_simple_init_config.max_steps = 100000
yolo_xo_simple_init_config.patience = 5000

yolo_xo_simple_continue_config = yolo_xo_simple_config.copy(
    alg_name="yolo_xo_simple_continue",
    balanced=True,
    n_train=1000,
    n_samples_per_image=1,
    curriculum=[dict()],
    load_path="/media/data/dps_data/logs/local_run_env=xo/exp_alg=yolo_xo_simple_init_seed=525580444_2018_06_03_11_03_59/weights/best_of_stage_0",
)

yolo_xo_simple_continue_config.update(curriculum_2stage[1])
yolo_xo_simple_continue_config.max_steps = 100000
yolo_xo_simple_continue_config.patience = 5000