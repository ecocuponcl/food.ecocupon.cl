-- ═══════════════════════════════════════════════════════
-- SUPABASE VAULT — Cloudflare API Token
-- ═══════════════════════════════════════════════════════

-- 1. Extensión
create extension if not exists pgsodium;

-- 2. Tabla
create table if not exists secrets_vault (
    name            text primary key,
    encrypted_key   uuid not null default pgsodium.create_key(),
    encrypted_value bytea not null,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- 3. Set secret (upsert)
create or replace function set_secret(secret_name text, secret_value text)
returns void language plpgsql security definer as $$
declare key_id uuid := pgsodium.create_key();
begin
    insert into secrets_vault (name, encrypted_key, encrypted_value)
    values (secret_name, key_id, pgsodium.crypto_aead_det_encrypt(
        secret_value::bytea, null::bytea, key_id
    ))
    on conflict (name) do update
    set encrypted_value = pgsodium.crypto_aead_det_encrypt(
        secret_value::bytea, null::bytea,
        (select encrypted_key from secrets_vault where name = secret_name)
    ),
    updated_at = now();
end;
$$;

-- 4. Get secret
create or replace function get_secret(secret_name text)
returns text language plpgsql security definer as $$
declare key_id uuid;
begin
    select encrypted_key into key_id
    from secrets_vault where name = secret_name;

    return convert_from(
        pgsodium.crypto_aead_det_decrypt(
            (select encrypted_value from secrets_vault where name = secret_name),
            null::bytea, key_id
        ),
        'UTF8'
    );
end;
$$;

-- 5. Seguridad
revoke all on secrets_vault from public, anon, authenticated;

-- 6. Guardar token Cloudflare
select set_secret(
    'CLOUDFLARE_API_TOKEN',
    'cfut_YixFEEBIyoZbGdNoNH4yvHSgsrhsaLox7KDNbVm5719cfc37'
);

-- 7. Verificar
select get_secret('CLOUDFLARE_API_TOKEN');
