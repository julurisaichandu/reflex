-- Reflex Exchange — Supabase schema
-- Minimal, demo-driven. Every table serves the A→B→C→D flow.

create extension if not exists pgcrypto;

-- Agents (lightweight identity; no auth for the demo)
create table agents (
  id          text primary key,              -- "agent-a", "agent-b", ...
  display_name text,
  created_at  timestamptz not null default now()
);

-- ProofPacks
create table packs (
  id              text primary key default ('pk_' || substr(gen_random_uuid()::text, 1, 8)),
  seller_agent_id text not null references agents(id),
  title           text not null,
  task_signature  text not null,             -- searchable problem statement
  description     text,
  trace           jsonb not null,            -- steps + solution_files (the merchandise)
  tests           jsonb not null,            -- [{cmd, expect_exit}]
  env_fingerprint jsonb not null,            -- seller's origin environment
  price_cents     integer not null default 100 check (price_cents >= 50), -- Stripe min
  custos_status   text not null default 'unverified'
                  check (custos_status in ('verified','unverified','pending')),
  created_at      timestamptz not null default now()
);
create index packs_search_idx on packs using gin (to_tsvector('english', title || ' ' || task_signature));

-- Transactions (one per acquire)
create table transactions (
  id                        text primary key default ('tx_' || substr(gen_random_uuid()::text, 1, 8)),
  pack_id                   text not null references packs(id),
  buyer_agent_id            text not null references agents(id),
  buyer_env_fingerprint     jsonb not null,
  stripe_payment_intent_id  text not null,
  amount_cents              integer not null,
  status                    text not null default 'authorized'
                            check (status in ('authorized','captured','canceled')),
  created_at                timestamptz not null default now(),
  resolved_at               timestamptz
);

-- Verifications (one per verify_and_settle run; the evidence record)
create table verifications (
  id              text primary key default ('vf_' || substr(gen_random_uuid()::text, 1, 8)),
  transaction_id  text not null references transactions(id),
  pack_id         text not null references packs(id),
  fixture         text not null,             -- e.g. 'py311-pip'
  env_fingerprint jsonb not null,
  result          text not null check (result in ('pass','fail')),
  evidence        jsonb,                     -- REDACTED evidence only (see redact.py)
  duration_ms     integer,
  created_at      timestamptz not null default now()
);

-- Warnings (free negative knowledge; byproduct of failed verifications)
create table warnings (
  id              text primary key default ('wn_' || substr(gen_random_uuid()::text, 1, 8)),
  pack_id         text not null references packs(id),
  verification_id text not null references verifications(id),
  env_fingerprint jsonb not null,            -- the environment this warning applies to
  summary         text not null,             -- human/agent-readable, sanitized
  evidence        jsonb,                     -- {exit_code, error_class, failed_test}
  created_at      timestamptz not null default now()
);
create index warnings_pack_idx on warnings (pack_id);

-- Compatibility view: per-pack, per-environment pass/fail tallies.
-- Match key = language + language_version + package_manager.
create view pack_compatibility as
select
  v.pack_id,
  (v.env_fingerprint->>'language')          as language,
  (v.env_fingerprint->>'language_version')  as language_version,
  (v.env_fingerprint->>'package_manager')   as package_manager,
  count(*) filter (where v.result = 'pass') as passes,
  count(*) filter (where v.result = 'fail') as fails,
  max(v.created_at)                         as last_observed
from verifications v
group by 1, 2, 3, 4;

-- Seed agents for the demo
insert into agents (id, display_name) values
  ('agent-a', 'Seller Agent A'),
  ('agent-b', 'Buyer Agent B'),
  ('agent-c', 'Buyer Agent C'),
  ('agent-d', 'Buyer Agent D')
on conflict do nothing;
