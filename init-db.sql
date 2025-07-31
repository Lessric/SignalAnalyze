-- Oscilloscope Analysis Database Schema
-- This will run automatically when PostgreSQL starts

-- DTT Analysis Table
CREATE TABLE IF NOT EXISTS dtt_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- DC02 Analysis Table (includes ringdown)
CREATE TABLE IF NOT EXISTS dc02_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    ringdown_voltage_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    ringdown_lsl DECIMAL(10,3),
    ringdown_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- DTR Analysis Table
CREATE TABLE IF NOT EXISTS dtr_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl_spin DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- DC03 Skid Analysis Table
CREATE TABLE IF NOT EXISTS dc03_skid_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- IDOD Analysis Table (includes skid plate diameter)
CREATE TABLE IF NOT EXISTS idod_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    skid_plate_diameter VARCHAR(50),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- Insert sample data for testing
INSERT INTO dtt_analysis (
    file_name, test_number, test_bench, tester_id, test_date, test_function,
    dut_device, reference_device, peak_to_peak_mv, trigger_current_a, noise_mv,
    frequency_khz, data_points, sample_rate_khz, peak_to_peak_lsl, peak_to_peak_usl,
    trigger_current_lsl, trigger_current_usl, noise_lsl, noise_usl, trigger_events, pass_fail
) VALUES (
    'sample_test.csv', 'T001', 'Bench A', 'admin', CURRENT_DATE, 'Performance test',
    'DTT (SV/33053/0020) [DUT]', 'DTR (SV/33053/0031) [Reference]', 350.5, 55.2, 2.1,
    250.0, 2000, 250.0, 150, 400, 30, 80, 0, 5, 3, 'pass'
);
