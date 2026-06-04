# RAPIDA Database Setup Guide
**PostgreSQL 16 + PostGIS on Ubuntu Linux Server**

---

## Prerequisites
- Ubuntu 24.04 Linux server
- Root or sudo access
- PostgreSQL 16 installed

---

## Step 1 — Install PostgreSQL & PostGIS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install PostGIS for PostgreSQL 16
sudo apt install postgis postgresql-16-postgis-3 -y
```

---

## Step 2 — Start & Enable PostgreSQL

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Enable on boot
sudo systemctl enable postgresql

# Confirm running
sudo systemctl status postgresql
```

---

## Step 3 — Allow Remote Connections

### 3a. Edit postgresql.conf
```bash
sudo nano /etc/postgresql/16/main/postgresql.conf
```

Find and change:
```
#listen_addresses = 'localhost'
```
To:
```
listen_addresses = '*'
```

### 3b. Edit pg_hba.conf
```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Add this line at the bottom:
```
host    rapida_db    rapida_user    0.0.0.0/0    md5
```

### 3c. Restart PostgreSQL
```bash
sudo pg_ctlcluster 16 main restart
```

### 3d. Verify Listening on All Interfaces
```bash
ss -tlnp | grep 5432
```

Expected output:
```
LISTEN 0      200          0.0.0.0:5432      0.0.0.0:*
LISTEN 0      200             [::]:5432         [::]:*
```

---

## Step 4 — Create Database & User

```bash
# Switch to postgres system user
sudo -i -u postgres

# Open PostgreSQL shell
psql
```

Inside psql:

```sql
-- Create a dedicated user
CREATE USER rapida_user WITH PASSWORD 'your_strong_password_here';

-- Create the database
CREATE DATABASE rapida_db OWNER rapida_user;

-- Connect to the database
\c rapida_db

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Exit
\q
```

Exit postgres user:
```bash
exit
```

---

## Step 5 — Create Tables, Indexes, Views & Triggers

Connect as rapida_user:
```bash
psql -U rapida_user -d rapida_db -h localhost
```

Paste and run the full schema below:

```sql
-- ============================================================
-- TABLE 1: crisis_report
-- ============================================================
CREATE TABLE crisis_report (
    -- Identity
    report_id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name                      VARCHAR(200) NOT NULL,
    event_id                        VARCHAR(100) NOT NULL,

    -- Versioning
    version_number                  INTEGER NOT NULL DEFAULT 1,
    is_latest                       BOOLEAN NOT NULL DEFAULT TRUE,
    previous_report_id              UUID REFERENCES crisis_report(report_id),

    -- Location
    lat                             DOUBLE PRECISION,
    long                            DOUBLE PRECISION,
    location                        GEOMETRY(Point, 4326),
    location_text                   TEXT,
    fishnet_id                      VARCHAR(50),

    -- Infrastructure
    infrastructure_type             VARCHAR(100) NOT NULL,
    infrastructure_type_other       TEXT,
    infrastructure_name             VARCHAR(200),
    no_of_damaged_infrastructures   INTEGER DEFAULT 1,

    -- Crisis Classification
    nature_of_crisis                VARCHAR(50) NOT NULL,

    -- Damage
    damage_level                    VARCHAR(20) NOT NULL,
    debris_needs_clearing           BOOLEAN NOT NULL DEFAULT FALSE,
    description                     TEXT,

    -- Media (URLs to local filesystem or object store)
    photos                          JSONB DEFAULT '[]',

    -- AI Analysis
    ai_damage_level                 VARCHAR(20),
    ai_confidence_score             FLOAT,
    ai_description                  TEXT,

    -- Submitter (anonymized)
    submitter_token                 VARCHAR(255),
    submission_channel              VARCHAR(50),
    language                        VARCHAR(10),

    -- Duplicate Detection
    is_duplicate                    BOOLEAN DEFAULT FALSE,
    duplicate_of_report_id          UUID REFERENCES crisis_report(report_id),

    -- Verification
    is_verified                     BOOLEAN DEFAULT FALSE,
    verified_by                     UUID,
    verified_at                     TIMESTAMP,

    -- Modular / Custom Questions
    custom_responses                JSONB DEFAULT '{}',

    -- Response Status
    respondence_status              VARCHAR(50) DEFAULT 'pending',
    respondence_time                TIMESTAMP,

    -- Timestamps
    submission_timestamp            TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated                    TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TABLE 2: responders
-- ============================================================
CREATE TABLE responders (
    responder_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    responder_name     VARCHAR(150) NOT NULL,
    email              VARCHAR(255) UNIQUE NOT NULL,
    password_hash      TEXT NOT NULL,
    role               VARCHAR(50) NOT NULL,
    organization       VARCHAR(150),
    active             BOOLEAN DEFAULT TRUE,
    created_at         TIMESTAMP DEFAULT NOW(),
    last_login         TIMESTAMP
);

-- ============================================================
-- TABLE 3: assignment
-- ============================================================
CREATE TABLE assignment (
    assignment_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id          UUID NOT NULL REFERENCES crisis_report(report_id),
    responder_id       UUID NOT NULL REFERENCES responders(responder_id),
    assigned_by        UUID REFERENCES responders(responder_id),
    assigned_at        TIMESTAMP DEFAULT NOW(),
    due_date           DATE,
    status             VARCHAR(50) DEFAULT 'pending',
    priority           VARCHAR(20) DEFAULT 'normal',
    notes              TEXT,
    completed_at       TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Spatial index for map queries
CREATE INDEX idx_crisis_report_location
    ON crisis_report USING GIST(location);

-- Fast lookup of latest report per location
CREATE INDEX idx_crisis_report_is_latest
    ON crisis_report(is_latest) WHERE is_latest = TRUE;

-- Filter by event
CREATE INDEX idx_crisis_report_event_id
    ON crisis_report(event_id);

-- Filter by damage level
CREATE INDEX idx_crisis_report_damage_level
    ON crisis_report(damage_level);

-- Duplicate detection
CREATE INDEX idx_crisis_report_submitter_token
    ON crisis_report(submitter_token);

-- Assignment lookups
CREATE INDEX idx_assignment_responder_id
    ON assignment(responder_id);

CREATE INDEX idx_assignment_report_id
    ON assignment(report_id);

-- ============================================================
-- VIEWS
-- ============================================================

-- Latest reports only (for dashboard)
CREATE VIEW latest_crisis_reports AS
SELECT * FROM crisis_report
WHERE is_latest = TRUE
AND is_duplicate = FALSE;

-- Clean export view (for CSV/GeoJSON export to UNDP)
CREATE VIEW export_crisis_reports AS
SELECT
    report_id,
    event_id,
    event_name,
    nature_of_crisis,
    infrastructure_type,
    infrastructure_name,
    damage_level,
    debris_needs_clearing,
    description,
    lat,
    long,
    location_text,
    submission_channel,
    language,
    respondence_status,
    submission_timestamp,
    version_number,
    is_verified,
    custom_responses
FROM crisis_report
WHERE is_latest = TRUE
AND is_duplicate = FALSE;

-- ============================================================
-- TRIGGER: Auto-update is_latest on new version submission
-- ============================================================
CREATE OR REPLACE FUNCTION update_is_latest()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.previous_report_id IS NOT NULL THEN
        UPDATE crisis_report
        SET is_latest = FALSE
        WHERE report_id = NEW.previous_report_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_is_latest
AFTER INSERT ON crisis_report
FOR EACH ROW
EXECUTE FUNCTION update_is_latest();
```

---

## Relationships

### `assignment` → `crisis_report`
- `assignment.report_id` → `crisis_report.report_id`
- One report can have many assignments. A field enumerator is sent to follow up on a specific report.

### `assignment` → `responders`
- `assignment.responder_id` → `responders.responder_id`
- `assignment.assigned_by` → `responders.responder_id`
- One responder can have many assignments. `assigned_by` tracks which supervisor created the assignment.

### `crisis_report` → `crisis_report` (Self-referencing)
- `crisis_report.previous_report_id` → `crisis_report.report_id`
- `crisis_report.duplicate_of_report_id` → `crisis_report.report_id`

Two self-references on the same table:
- `previous_report_id` — links a new report version to the old one (versioning)
- `duplicate_of_report_id` — links a duplicate report to the original


## Step 6 — Verify Everything

Run these inside psql:

```sql
-- List all tables
\dt

-- List all views
\dv

-- List all indexes
\di

-- Confirm PostGIS is working
SELECT PostGIS_Version();

-- Confirm trigger exists
\df update_is_latest
```

---

## Step 7 — Connect from pgAdmin

In pgAdmin, right click **Servers → Register → Server** and fill in:

| Field | Value |
|---|---|
| Name | RAPIDA DB |
| Host | your_server_ip |
| Port | 5432 |
| Database | rapida_db |
| Username | rapida_user |
| Password | your_strong_password_here |

To find your server IP:
```bash
curl ifconfig.me
```

---

## Field Reference

### crisis_report — Key Field Values

| Field | Allowed Values |
|---|---|
| `infrastructure_type` | `residential` \| `commercial` \| `government` \| `utility` \| `transport_communication` \| `community` \| `public_recreation` \| `other` |
| `nature_of_crisis` | `earthquake` \| `flood` \| `tsunami` \| `hurricane_cyclone` \| `wildfire` \| `explosion` \| `chemical_incident` \| `conflict` \| `civil_unrest` |
| `damage_level` | `minimal` \| `partial` \| `complete` |
| `submission_channel` | `web` \| `mobile` \| `whatsapp` \| `offline_sync` |
| `language` | `en` \| `ar` \| `fr` \| `zh` \| `ru` \| `es` |
| `respondence_status` | `pending` \| `acknowledged` \| `in_progress` \| `resolved` |

### responders — Key Field Values

| Field | Allowed Values |
|---|---|
| `role` | `admin` \| `field_enumerator` \| `analyst` \| `supervisor` |

### assignment — Key Field Values

| Field | Allowed Values |
|---|---|
| `status` | `pending` \| `in_progress` \| `completed` \| `cancelled` |
| `priority` | `low` \| `normal` \| `high` \| `critical` |

---

## Photos JSONB Structure

```json
[
  {
    "url": "/uploads/reports/photo1.jpg",
    "thumbnail_url": "/uploads/reports/photo1_thumb.jpg",
    "is_primary": true,
    "uploaded_at": "2026-06-04T10:00:00Z"
  }
]
```

> In production, swap local file paths for object store URLs (S3/MinIO).

---

## Custom Responses JSONB Structure

```json
{
  "livelihood_impact": "severe",
  "water_access": false,
  "days_displaced": 14
}
```

---

## Scalability Note

> The MVP uses a consolidated 3-table schema optimized for rapid prototyping. In production, `photos` would migrate to a dedicated `media` table backed by object storage, `crisis_event` would be normalized into its own table to eliminate row-level redundancy, and `buildings` footprints would be managed as a separate PostGIS layer. The core fields and relationships remain identical — the transition is purely structural.
