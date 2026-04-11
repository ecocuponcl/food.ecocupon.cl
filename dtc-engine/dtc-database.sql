-- ============================================
-- DTC ENGINE: Código de Falla → Repuestos
-- Base de datos automotriz para diagnóstico
-- ============================================

CREATE TABLE IF NOT EXISTS dtc_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dtc_code TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    description_es TEXT NOT NULL,
    severity TEXT DEFAULT 'medium', -- low, medium, high, critical
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dtc_parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dtc_code TEXT NOT NULL,
    part_name TEXT NOT NULL,
    part_category TEXT NOT NULL,
    priority INTEGER DEFAULT 1, -- 1 = más probable, 5 = menos probable
    estimated_cost_clp INTEGER DEFAULT 0,
    FOREIGN KEY (dtc_code) REFERENCES dtc_codes(dtc_code)
);

-- ============================================
-- INSERTAR CÓDIGOS DTC PRINCIPALES
-- ============================================

-- MOTOR (P0xxx)
INSERT INTO dtc_codes (dtc_code, category, description_es, severity) VALUES
('P0300', 'Motor', 'Fallo de encendido aleatorio/múltiple cilindro', 'high'),
('P0301', 'Motor', 'Fallo de encendido cilindro 1', 'high'),
('P0302', 'Motor', 'Fallo de encendido cilindro 2', 'high'),
('P0303', 'Motor', 'Fallo de encendido cilindro 3', 'high'),
('P0304', 'Motor', 'Fallo de encendido cilindro 4', 'high'),
('P0420', 'Emisiones', 'Eficiencia del catalizador por debajo del umbral', 'medium'),
('P0440', 'Emisiones', 'Fuga en sistema EVAP', 'low'),
('P0100', 'Sensor', 'Fallo circuito MAF (caudalímetro)', 'medium'),
('P0171', 'Motor', 'Mezcla demasiado pobre (banco 1)', 'medium'),
('P0172', 'Motor', 'Mezcla demasiado rica (banco 1)', 'medium'),
('P0400', 'Emisiones', 'Fallo flujo EGR', 'medium'),
('P0500', 'Velocidad', 'Fallo sensor velocidad vehículo', 'medium'),
('P0600', 'Comunicación', 'Fallo comunicación serie', 'high'),
('P0700', 'Transmisión', 'Fallo sistema control transmisión', 'high'),
('P0455', 'Emisiones', 'Fuga grande sistema EVAP', 'medium');

-- REPUESTOS POR DTC
-- P0300-P0304: Fallo de encendido
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0300', 'Bujías (set completo)', 'Encendido', 1, 35000),
('P0300', 'Bobinas de encendido', 'Encendido', 2, 85000),
('P0300', 'Cables de bujía', 'Encendido', 3, 25000),
('P0300', 'Inyectores de combustible', 'Combustible', 4, 120000),
('P0301', 'Bujía cilindro 1', 'Encendido', 1, 8000),
('P0301', 'Bobina cilindro 1', 'Encendido', 2, 22000),
('P0302', 'Bujía cilindro 2', 'Encendido', 1, 8000),
('P0302', 'Bobina cilindro 2', 'Encendido', 2, 22000),
('P0303', 'Bujía cilindro 3', 'Encendido', 1, 8000),
('P0303', 'Bobina cilindro 3', 'Encendido', 2, 22000),
('P0304', 'Bujía cilindro 4', 'Encendido', 1, 8000),
('P0304', 'Bobina cilindro 4', 'Encendido', 2, 22000);

-- P0420: Catalizador
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0420', 'Catalizador completo', 'Emisiones', 1, 350000),
('P0420', 'Sensor oxígeno upstream', 'Sensores', 2, 45000),
('P0420', 'Sensor oxígeno downstream', 'Sensores', 3, 45000),
('P0420', 'Junta de escape', 'Escape', 4, 15000);

-- P0440/P0455: Sistema EVAP
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0440', 'Válvula purga EVAP', 'Emisiones', 1, 35000),
('P0440', 'Tapa combustible', 'Emisiones', 2, 12000),
('P0440', 'Manguera EVAP', 'Emisiones', 3, 18000),
('P0455', 'Válvula purga EVAP', 'Emisiones', 1, 35000),
('P0455', 'Tanque de carbón activo', 'Emisiones', 2, 65000),
('P0455', 'Manguera EVAP', 'Emisiones', 3, 18000);

-- P0100: Caudalímetro
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0100', 'Sensor MAF (caudalímetro)', 'Sensores', 1, 75000),
('P0100', 'Filtro de aire', 'Filtros', 2, 12000),
('P0100', 'Conector sensor MAF', 'Eléctrico', 3, 8000);

-- P0171/P0172: Mezcla combustible
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0171', 'Sensor oxígeno upstream', 'Sensores', 1, 45000),
('P0171', 'Inyectores de combustible', 'Combustible', 2, 120000),
('P0171', 'Bomba de combustible', 'Combustible', 3, 95000),
('P0171', 'Filtro de combustible', 'Filtros', 4, 15000),
('P0172', 'Sensor oxígeno upstream', 'Sensores', 1, 45000),
('P0172', 'Regulador de presión combustible', 'Combustible', 2, 55000),
('P0172', 'Válvula PCV', 'Motor', 3, 18000);

-- P0400: EGR
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0400', 'Válvula EGR', 'Emisiones', 1, 65000),
('P0400', 'Manguera EGR', 'Emisiones', 2, 15000),
('P0400', 'Sensor de presión diferencial', 'Sensores', 3, 35000);

-- P0500: Velocidad
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0500', 'Sensor velocidad vehículo (VSS)', 'Sensores', 1, 45000),
('P0500', 'Cableado sensor VSS', 'Eléctrico', 2, 15000),
('P0500', 'Conector sensor VSS', 'Eléctrico', 3, 8000);

-- P0700: Transmisión
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0700', 'Módulo control transmisión (TCM)', 'Transmisión', 1, 185000),
('P0700', 'Solenoide cambio', 'Transmisión', 2, 65000),
('P0700', 'Sensor velocidad entrada', 'Transmisión', 3, 45000),
('P0700', 'Fluido transmisión ATF', 'Fluidos', 4, 35000);

-- P0600: Comunicación
INSERT INTO dtc_parts (dtc_code, part_name, part_category, priority, estimated_cost_clp) VALUES
('P0600', 'Módulo ECM/PCM', 'Computador', 1, 250000),
('P0600', 'Cableado CAN bus', 'Eléctrico', 2, 45000),
('P0600', 'Fusible principal ECM', 'Eléctrico', 3, 5000);
