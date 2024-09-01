#include <cmath>
#include <cstdlib>
#include <deque>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

struct VehicleState {
    double timestamp;
    double speed_mps;
    double brake_force;
    double lane_offset_m;
    double obstacle_distance_m;
    double steering_deg;
    std::string camera_frame_id;
};

struct EventRecord {
    std::string event_id;
    std::string event_type;
    VehicleState trigger;
    std::vector<VehicleState> pre_context;
    std::vector<VehicleState> post_context;
};

struct PendingCapture {
    std::string event_id;
    std::string event_type;
    VehicleState trigger;
    std::vector<VehicleState> pre_context;
    std::vector<VehicleState> post_context;
    int remaining_post_ticks;
};

struct Config {
    int steps = 120;
    int seed = 7;
    std::string vehicle_id = "vehicle_sim_001";
    int pre_context_ticks = 20;
    int post_context_ticks = 30;
    int batch_size = 8;
    int max_retries = 4;
    double flush_interval_s = 1.0;
    double retry_base_delay_s = 0.2;
    double retry_jitter_s = 0.15;
    double transport_fail_rate = 0.2;
    bool quiet = false;
};

struct Metrics {
    int states_processed = 0;
    int events_detected = 0;
    int events_packaged = 0;
    int batches_sent = 0;
    int batches_dropped = 0;
    int transport_failures = 0;
    int retry_attempts = 0;
    int max_retry_queue_depth = 0;
};

// Classify each state into the event type that should be captured.
std::string detect_event(const VehicleState& state) {
    if (state.brake_force > 0.8 && state.speed_mps > 18.0) {
        return "hard_brake";
    }
    if (std::abs(state.lane_offset_m) > 0.5) {
        return "lane_departure";
    }
    if (state.obstacle_distance_m < 8.0 && state.speed_mps > 10.0) {
        return "sudden_obstacle";
    }
    return "";
}


// Build a stable event identifier for logs and payloads.
std::string make_event_id(int tick, const std::string& prefix = "cpp_evt_") {
    std::ostringstream out;
    out << prefix << std::setw(6) << std::setfill('0') << tick;
    return out.str();
}


// Escape quote characters so JSON output stays valid.
std::string json_escape(const std::string& in) {
    std::string out;
    out.reserve(in.size());
    for (char c : in) {
        if (c == '"') {
            out += "\\\"";
        } else {
            out += c;
        }
    }
    return out;
}


// Serialize a single vehicle snapshot into a JSON object string.
std::string state_json(const VehicleState& state) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(3);
    out << "{";
    out << "\"timestamp\":" << state.timestamp << ",";
    out << "\"speed_mps\":" << state.speed_mps << ",";
    out << "\"brake_force\":" << state.brake_force << ",";
    out << "\"lane_offset_m\":" << state.lane_offset_m << ",";
    out << "\"obstacle_distance_m\":" << state.obstacle_distance_m << ",";
    out << "\"steering_deg\":" << state.steering_deg << ",";
    out << "\"camera_frame_id\":\"" << state.camera_frame_id << "\"";
    out << "}";
    return out.str();
}


// Serialize a vector of snapshots into a JSON array string.
std::string states_array_json(const std::vector<VehicleState>& states) {
    std::ostringstream out;
    out << "[";
    for (size_t i = 0; i < states.size(); ++i) {
        if (i > 0) {
            out << ",";
        }
        out << state_json(states[i]);
    }
    out << "]";
    return out.str();
}


// Infer a synthetic text command to simulate operator intent.
std::string infer_operator_command(const std::string& event_type) {
    if (event_type == "hard_brake") {
        return "slow down";
    }
    if (event_type == "lane_departure") {
        return "maintain speed";
    }
    if (event_type == "sudden_obstacle") {
        return "pull over";
    }
    return "reroute";
}


// Build compact vision metadata so C++ events are multimodal too.
std::string vision_json(const EventRecord& event) {
    std::ostringstream out;
    std::string lighting = (static_cast<int>(event.trigger.timestamp) % 2 == 0) ? "day" : "night";
    std::string scene_hint = (event.trigger.obstacle_distance_m < 10.0) ? "near_obstacle" : "clear_path";
    out << "{";
    out << "\"frame_id\":\"" << event.trigger.camera_frame_id << "\",";
    out << "\"lighting\":\"" << lighting << "\",";
    out << "\"scene_hint\":\"" << scene_hint << "\"";
    out << "}";
    return out.str();
}


// Serialize one fully packaged telemetry event.
std::string event_json(const EventRecord& event, const Config& config) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(3);
    out << "{";
    out << "\"schema_version\":\"1.0\",";
    out << "\"event_id\":\"" << event.event_id << "\",";
    out << "\"event_type\":\"" << event.event_type << "\",";
    out << "\"timestamp\":" << event.trigger.timestamp << ",";
    out << "\"vehicle_id\":\"" << json_escape(config.vehicle_id) << "\",";
    out << "\"source\":{";
    out << "\"device_type\":\"edge_simulator\",";
    out << "\"firmware_version\":\"wk3-4\",";
    out << "\"simulator\":\"cpp\"";
    out << "},";
    out << "\"operator_command\":\"" << infer_operator_command(event.event_type) << "\",";
    out << "\"vision\":" << vision_json(event) << ",";
    out << "\"state\":" << state_json(event.trigger) << ",";
    out << "\"context\":{";
    out << "\"pre_context\":" << states_array_json(event.pre_context) << ",";
    out << "\"post_context\":" << states_array_json(event.post_context) << ",";
    out << "\"pre_ticks\":" << config.pre_context_ticks << ",";
    out << "\"post_ticks\":" << config.post_context_ticks;
    out << "}";
    out << "}";
    return out.str();
}


// Join multiple event JSON documents into NDJSON text.
std::string join_ndjson(const std::vector<EventRecord>& events, const Config& config) {
    std::ostringstream out;
    for (size_t i = 0; i < events.size(); ++i) {
        if (i > 0) {
            out << "\n";
        }
        out << event_json(events[i], config);
    }
    return out.str();
}


// Build the final batch envelope sent by the C++ edge runtime.
std::string batch_json(
    const std::vector<EventRecord>& events,
    const Config& config,
    int batch_index,
    const std::string& payload,
    bool sent_ok
) {
    std::ostringstream out;
    out << "{";
    out << "\"batch_id\":\"" << make_event_id(batch_index, "cpp_batch_") << "\",";
    out << "\"schema_version\":\"1.0\",";
    out << "\"vehicle_id\":\"" << json_escape(config.vehicle_id) << "\",";
    out << "\"event_count\":" << events.size() << ",";
    out << "\"encoding\":\"ndjson\",";
    out << "\"compression\":\"none\",";
    out << "\"delivery\":\"" << (sent_ok ? "sent" : "dropped") << "\",";
    out << "\"payload\":\"" << json_escape(payload) << "\"";
    out << "}";
    return out.str();
}


// Attempt batch delivery with retry and backoff accounting.
bool send_with_retries(
    const std::vector<EventRecord>& events,
    const Config& config,
    std::mt19937& rng,
    Metrics& metrics,
    int batch_index
) {
    std::uniform_real_distribution<double> fail_dist(0.0, 1.0);
    std::uniform_real_distribution<double> jitter_dist(0.0, config.retry_jitter_s);
    std::string payload = join_ndjson(events, config);
    int attempts = 0;
    while (attempts <= config.max_retries) {
        attempts += 1;
        bool failed = fail_dist(rng) < config.transport_fail_rate;
        if (!failed) {
            metrics.batches_sent += 1;
            if (!config.quiet) {
                std::cout << batch_json(events, config, batch_index, payload, true) << "\n";
            }
            return true;
        }
        metrics.transport_failures += 1;
        if (attempts <= config.max_retries) {
            metrics.retry_attempts += 1;
            volatile double ignored_backoff = config.retry_base_delay_s * std::pow(2.0, attempts - 1) + jitter_dist(rng);
            (void)ignored_backoff;
        }
    }
    metrics.batches_dropped += 1;
    if (!config.quiet) {
        std::cout << batch_json(events, config, batch_index, payload, false) << "\n";
    }
    return false;
}


// Parse CLI flags into runtime configuration.
Config parse_args(int argc, char* argv[]) {
    Config config;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--steps" && i + 1 < argc) {
            config.steps = std::atoi(argv[++i]);
        } else if (arg == "--seed" && i + 1 < argc) {
            config.seed = std::atoi(argv[++i]);
        } else if (arg == "--vehicle-id" && i + 1 < argc) {
            config.vehicle_id = argv[++i];
        } else if (arg == "--pre-context" && i + 1 < argc) {
            config.pre_context_ticks = std::atoi(argv[++i]);
        } else if (arg == "--post-context" && i + 1 < argc) {
            config.post_context_ticks = std::atoi(argv[++i]);
        } else if (arg == "--batch-size" && i + 1 < argc) {
            config.batch_size = std::atoi(argv[++i]);
        } else if (arg == "--max-retries" && i + 1 < argc) {
            config.max_retries = std::atoi(argv[++i]);
        } else if (arg == "--flush-interval" && i + 1 < argc) {
            config.flush_interval_s = std::atof(argv[++i]);
        } else if (arg == "--retry-base-delay" && i + 1 < argc) {
            config.retry_base_delay_s = std::atof(argv[++i]);
        } else if (arg == "--retry-jitter" && i + 1 < argc) {
            config.retry_jitter_s = std::atof(argv[++i]);
        } else if (arg == "--transport-fail-rate" && i + 1 < argc) {
            config.transport_fail_rate = std::atof(argv[++i]);
        } else if (arg == "--quiet") {
            config.quiet = true;
        }
    }
    return config;
}


// Print a compact metrics report at the end of the run.
void print_metrics(const Metrics& metrics) {
    std::cerr << "{"
              << "\"metrics\":{"
              << "\"states_processed\":" << metrics.states_processed << ","
              << "\"events_detected\":" << metrics.events_detected << ","
              << "\"events_packaged\":" << metrics.events_packaged << ","
              << "\"batches_sent\":" << metrics.batches_sent << ","
              << "\"batches_dropped\":" << metrics.batches_dropped << ","
              << "\"transport_failures\":" << metrics.transport_failures << ","
              << "\"retry_attempts\":" << metrics.retry_attempts << ","
              << "\"max_retry_queue_depth\":" << metrics.max_retry_queue_depth
              << "}"
              << "}\n";
}


// Run the end-to-end C++ edge simulation and transport flow.
int main(int argc, char* argv[]) {
    Config config = parse_args(argc, argv);

    std::mt19937 rng(config.seed);
    std::uniform_real_distribution<double> accel_dist(-2.0, 2.5);
    std::uniform_real_distribution<double> lane_jitter(-0.04, 0.04);
    std::uniform_real_distribution<double> obstacle_jitter(-3.0, 3.0);
    std::uniform_real_distribution<double> brake_dist(0.0, 0.35);
    std::uniform_real_distribution<double> steer_noise(-2.0, 2.0);
    std::uniform_real_distribution<double> hard_brake_force(0.85, 1.0);
    std::uniform_real_distribution<double> hard_brake_speed_boost(4.0, 9.0);
    std::uniform_real_distribution<double> sudden_obstacle_dist(3.0, 7.5);

    double speed = 12.0;
    double lane_offset = 0.0;
    double obstacle_distance = 50.0;
    double base_ts = 1710000000.0;

    std::deque<VehicleState> ring_buffer;
    std::vector<PendingCapture> pending;
    std::vector<EventRecord> batch;
    Metrics metrics;
    int batch_index = 0;
    double batch_start_ts = -1.0;

    for (int tick = 1; tick <= config.steps; ++tick) {
        speed = std::max(0.0, speed + accel_dist(rng) * 0.1);
        lane_offset += lane_jitter(rng);
        lane_offset = std::max(-1.2, std::min(1.2, lane_offset));
        obstacle_distance = std::max(1.0, obstacle_distance + obstacle_jitter(rng));
        double brake_force = std::max(0.0, std::min(1.0, brake_dist(rng)));

        if (tick % 35 == 0) {
            brake_force = hard_brake_force(rng);
            speed = std::max(18.5, speed + hard_brake_speed_boost(rng));
        }
        if (tick % 40 == 0) {
            lane_offset = (tick % 80 == 0) ? 0.95 : -0.9;
        }
        if (tick % 45 == 0) {
            obstacle_distance = sudden_obstacle_dist(rng);
            speed = std::max(10.5, speed);
        }

        VehicleState state{
            base_ts + tick * 0.1,
            speed,
            brake_force,
            lane_offset,
            obstacle_distance,
            lane_offset * 18.0 + steer_noise(rng),
            "frame_" + std::to_string(tick),
        };

        metrics.states_processed += 1;
        ring_buffer.push_back(state);
        while (static_cast<int>(ring_buffer.size()) > config.pre_context_ticks + 1) {
            ring_buffer.pop_front();
        }

        std::string event_type = detect_event(state);
        if (!event_type.empty()) {
            metrics.events_detected += 1;
            PendingCapture capture;
            capture.event_id = make_event_id(tick, "cpp_evt_");
            capture.event_type = event_type;
            capture.trigger = state;
            capture.remaining_post_ticks = config.post_context_ticks;
            capture.pre_context.assign(ring_buffer.begin(), ring_buffer.end() - 1);
            pending.push_back(capture);
        }

        std::vector<size_t> completed;
        for (size_t idx = 0; idx < pending.size(); ++idx) {
            if (pending[idx].trigger.timestamp == state.timestamp) {
                continue;
            }
            if (pending[idx].remaining_post_ticks > 0) {
                pending[idx].post_context.push_back(state);
                pending[idx].remaining_post_ticks -= 1;
            }
            if (pending[idx].remaining_post_ticks == 0) {
                completed.push_back(idx);
            }
        }

        for (size_t i = completed.size(); i > 0; --i) {
            size_t idx = completed[i - 1];
            EventRecord event{
                pending[idx].event_id,
                pending[idx].event_type,
                pending[idx].trigger,
                pending[idx].pre_context,
                pending[idx].post_context,
            };
            batch.push_back(event);
            metrics.events_packaged += 1;
            if (batch_start_ts < 0.0) {
                batch_start_ts = state.timestamp;
            }
            pending.erase(pending.begin() + static_cast<long long>(idx));
        }

        bool flush_for_size = static_cast<int>(batch.size()) >= config.batch_size;
        bool flush_for_time = batch_start_ts >= 0.0 && (state.timestamp - batch_start_ts) >= config.flush_interval_s;
        if ((flush_for_size || flush_for_time) && !batch.empty()) {
            batch_index += 1;
            send_with_retries(batch, config, rng, metrics, batch_index);
            batch.clear();
            batch_start_ts = -1.0;
        }

        int retry_queue_depth = (metrics.transport_failures - metrics.batches_dropped - metrics.batches_sent);
        if (retry_queue_depth < 0) {
            retry_queue_depth = 0;
        }
        if (retry_queue_depth > metrics.max_retry_queue_depth) {
            metrics.max_retry_queue_depth = retry_queue_depth;
        }
    }

    for (const PendingCapture& remaining : pending) {
        EventRecord event{
            remaining.event_id,
            remaining.event_type,
            remaining.trigger,
            remaining.pre_context,
            remaining.post_context,
        };
        batch.push_back(event);
        metrics.events_packaged += 1;
    }
    if (!batch.empty()) {
        batch_index += 1;
        send_with_retries(batch, config, rng, metrics, batch_index);
    }

    print_metrics(metrics);
    return 0;
}

