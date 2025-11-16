-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    organization VARCHAR(255) NOT NULL,
    approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_approved (approved)
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    order_data JSON NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);

-- Note: assortment table should already exist in your database
-- If not, create it with the following structure:
-- CREATE TABLE IF NOT EXISTS assortment (
--     good_id INT PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     type VARCHAR(50),
--     price_c DECIMAL(10, 2),
--     price_amt DECIMAL(10, 2),
--     min_size DECIMAL(10, 2)
-- );

