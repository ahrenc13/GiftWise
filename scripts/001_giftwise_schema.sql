-- GiftWise Database Schema

-- Profiles table
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text,
  subscription_tier text default 'free',
  stripe_customer_id text,
  credits_remaining integer default 3,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table profiles enable row level security;

create policy "Users can view own profile" on profiles for select using (auth.uid() = id);
create policy "Users can update own profile" on profiles for update using (auth.uid() = id);
create policy "Users can insert own profile" on profiles for insert with check (auth.uid() = id);

-- OAuth connections
create table if not exists oauth_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade not null,
  platform text not null,
  platform_username text,
  access_token text,
  connected_at timestamptz default now(),
  is_active boolean default true,
  unique(user_id, platform)
);

alter table oauth_connections enable row level security;

create policy "Users can view own connections" on oauth_connections for select using (auth.uid() = user_id);
create policy "Users can manage own connections" on oauth_connections for all using (auth.uid() = user_id);

-- Social profiles
create table if not exists social_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade not null,
  recipient_name text not null,
  raw_data jsonb default '{}'::jsonb,
  interests text[],
  location text,
  budget_min numeric,
  budget_max numeric,
  created_at timestamptz default now()
);

alter table social_profiles enable row level security;

create policy "Users can view own social profiles" on social_profiles for select using (auth.uid() = user_id);
create policy "Users can manage own social profiles" on social_profiles for all using (auth.uid() = user_id);

-- Recommendation sessions
create table if not exists recommendation_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade not null,
  social_profile_id uuid references social_profiles(id) on delete cascade,
  status text default 'processing',
  catalog jsonb default '[]'::jsonb,
  selected_gifts jsonb default '[]'::jsonb,
  bespoke_packages jsonb default '[]'::jsonb,
  created_at timestamptz default now(),
  completed_at timestamptz
);

alter table recommendation_sessions enable row level security;

create policy "Users can view own sessions" on recommendation_sessions for select using (auth.uid() = user_id);
create policy "Users can manage own sessions" on recommendation_sessions for all using (auth.uid() = user_id);

-- Auto-create profile trigger
create or replace function handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', '')
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute function handle_new_user();
