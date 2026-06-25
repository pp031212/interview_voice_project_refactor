-- 创建数据库
CREATE DATABASE IF NOT EXISTS interview_voice DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE interview_voice;

-- 用户表
CREATE TABLE IF NOT EXISTS tb_user (
    user_id VARCHAR(32) PRIMARY KEY COMMENT '用户ID',
    user_name VARCHAR(100) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码',
    INDEX ind_user_id (user_id),
    INDEX ind_user_name (user_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 面试录音分析主表
CREATE TABLE IF NOT EXISTS tb_interview_recording_analysis (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '唯一标识ID',
    name VARCHAR(100) NOT NULL COMMENT '姓名',
    interview_time DATETIME NOT NULL COMMENT '面试时间',
    company_name VARCHAR(255) NOT NULL COMMENT '公司名',
    subject VARCHAR(255) NULL COMMENT '面试学科',
    recording_url VARCHAR(255) NOT NULL COMMENT '录音地址',
    processing_status SMALLINT DEFAULT 0 COMMENT '处理进度（0：未处理，1：正在处理，2：处理完成）',
    processing_tips LONGTEXT NULL COMMENT '处理提示',
    overall_comments LONGTEXT NULL COMMENT '整体点评',
    interview_score FLOAT NULL COMMENT '面试评分',
    strengths LONGTEXT NULL COMMENT '优势点',
    weaknesses LONGTEXT NULL COMMENT '不足点',
    improvement_suggestions LONGTEXT NULL COMMENT '改进建议',
    interview_text LONGTEXT NULL COMMENT '面试文本',
    markdown_text LONGTEXT NULL COMMENT '面试评价格式生成',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX ind_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试录音分析主表';

-- 面试录音分析明细表
CREATE TABLE IF NOT EXISTS tb_interview_recording_analysis_detail (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '唯一标识ID',
    interview_record_analysis_id VARCHAR(32) NOT NULL COMMENT '面试记录分析ID',
    interview_question TEXT NULL COMMENT '面试问题',
    interviewee_answer TEXT NULL COMMENT '面试者回答',
    reference_answer TEXT NULL COMMENT '参考答案',
    point_analysis TEXT NULL COMMENT '考点分析',
    answer_thoughts TEXT NULL COMMENT '答题思路',
    answer_evaluation TEXT NULL COMMENT '回答评价',
    answer_score FLOAT NULL COMMENT '回答评分',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试录音分析明细表';

-- ASR 分片缓存表（断点续传中间态，DB 主存）
CREATE TABLE IF NOT EXISTS tb_asr_segment_cache (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '唯一标识ID',
    record_id INT NOT NULL COMMENT '面试记录ID',
    segment_index INT NOT NULL COMMENT '音频分片序号（从0开始）',
    segment_path VARCHAR(1024) NOT NULL COMMENT '音频分片路径',
    segment_text LONGTEXT NOT NULL COMMENT 'ASR识别文本',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    UNIQUE KEY uk_record_segment (record_id, segment_index),
    INDEX ind_record_id (record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ASR分片缓存表';



-- Q&A 抽取缓存表（断点续传中间态，DB 主存）
CREATE TABLE IF NOT EXISTS tb_interview_extract_cache (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '唯一标识ID',
    record_id INT NOT NULL COMMENT '面试记录ID',
    qa_json LONGTEXT NOT NULL COMMENT 'Q&A 抽取结果(JSON字符串)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    UNIQUE KEY uk_extract_record_id (record_id),
    INDEX ind_extract_record_id (record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Q&A抽取缓存表';

-- 兼容旧库：将历史 TEXT 字段升级为 LONGTEXT
ALTER TABLE tb_interview_recording_analysis
MODIFY COLUMN markdown_text LONGTEXT COMMENT '面试评价格式生成';

ALTER TABLE tb_interview_recording_analysis
MODIFY COLUMN interview_text LONGTEXT COMMENT '面试文本';

ALTER TABLE tb_interview_recording_analysis
MODIFY COLUMN processing_tips LONGTEXT COMMENT '处理提示';

ALTER TABLE tb_interview_recording_analysis
MODIFY COLUMN overall_comments LONGTEXT COMMENT '整体点评';

ALTER TABLE tb_interview_recording_analysis
MODIFY COLUMN strengths LONGTEXT COMMENT '优势点';

ALTER TABLE tb_interview_recording_analysis
MODIFY COLUMN weaknesses LONGTEXT COMMENT '不足点';

ALTER TABLE tb_interview_recording_analysis
MODIFY COLUMN improvement_suggestions LONGTEXT COMMENT '改进建议';


-- 逐题分析缓存表（断点续传中间态，DB 主存）
CREATE TABLE IF NOT EXISTS tb_interview_analysis_cache (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '唯一标识ID',
    record_id INT NOT NULL COMMENT '面试记录ID',
    qa_index INT NOT NULL COMMENT '问答序号（从0开始）',
    qa_json LONGTEXT NOT NULL COMMENT '逐题分析结果(JSON字符串)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    UNIQUE KEY uk_analysis_record_index (record_id, qa_index),
    INDEX ind_analysis_record_id (record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='逐题分析缓存表';
