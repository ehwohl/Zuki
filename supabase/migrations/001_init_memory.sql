create table if not exists zuki_interactions (
    id          bigserial primary key,
    role        text        not null check (role in ('user', 'assistant', 'system')),
    content     text        not null,
    created_at  timestamptz not null default now()
);

create index idx_zuki_interactions_created_at on zuki_interactions (created_at desc);
