-- GiftWise Database Schema

-- Profiles table (extends auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text,
  subscription_tier text default 'free' check (subscription_tier in ('free', 'basic', 'premium')),
  stripe_customer_id text,
  credits_remaining integer default 3,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

alter table public.profiles enable row level security;

create policy "profiles_select_own" on public.profiles for select using (auth.uid() = id);
create policy "profiles_insert_own" on public.profiles for insert with check (auth.uid() = id);
create policy "profiles_update_own" on public.profiles for update using (auth.uid() = id);
create policy "profiles_delete_own" on public.profiles for delete using (auth.uid() = id);

-- OAuth connections table
create table if not exists public.oauth_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  platform text not null check (platform in ('instagram', 'tiktok', 'pinterest', 'spotify')),
  platform_user_id text,
  platform_username text,
  access_token text,
  refresh_token text,
  token_expires_at timestamp with time zone,
  connected_at timestamp with time zone default now(),
  last_synced_at timestamp with time zone,
  is_active boolean default true,
  unique(user_id, platform)
);

alter table public.oauth_connections enable row level security;

create policy "oauth_select_own" on public.oauth_connections for select using (auth.uid() = user_id);
create policy "oauth_insert_own" on public.oauth_connections for insert with check (auth.uid() = user_id);
create policy "oauth_update_own" on public.oauth_connections for update using (auth.uid() = user_id);
create policy "oauth_delete_own" on public.oauth_connections for delete using (auth.uid() = user_id);

-- Social profiles (scraped data from platforms)
create table if not exists public.social_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  recipient_name text not null,
  raw_data jsonb default '{}'::jsonb,
  interests jsonb default '[]'::jsonb,
  personality_traits jsonb default '[]'::jsonb,
  favorite_brands jsonb default '[]'::jsonb,
  music_taste jsonb default '{}'::jsonb,
  style_preferences jsonb default '{}'::jsonb,
  location text,
  age_range text,
  relationship text,
  budget_min numeric,
  budget_max numeric,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

alter table public.social_profiles enable row level security;

create policy "social_profiles_select_own" on public.social_profiles for select using (auth.uid() = user_id);
create policy "social_profiles_insert_own" on public.social_profiles for insert with check (auth.uid() = user_id);
create policy "social_profiles_update_own" on public.social_profiles for update using (auth.uid() = user_id);
create policy "social_profiles_delete_own" on public.social_profiles for delete using (auth.uid() = user_id);

-- Recommendation sessions
create table if not exists public.recommendation_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  social_profile_id uuid references public.social_profiles(id) on delete cascade not null,
  status text default 'processing' check (status in ('processing', 'completed', 'failed')),
  catalog jsonb default '[]'::jsonb, -- Array of 30 curated products
  selected_gifts jsonb default '[]'::jsonb, -- Final recommended products
  bespoke_packages jsonb default '[]'::jsonb, -- Custom experience packages
  ai_reasoning text, -- Claude's reasoning for selections
  created_at timestamp with time zone default now(),
  completed_at timestamp with time zone
);

alter table public.recommendation_sessions enable row level security;

create policy "rec_sessions_select_own" on public.recommendation_sessions for select using (auth.uid() = user_id);
create policy "rec_sessions_insert_own" on public.recommendation_sessions for insert with check (auth.uid() = user_id);
create policy "rec_sessions_update_own" on public.recommendation_sessions for update using (auth.uid() = user_id);
create policy "rec_sessions_delete_own" on public.recommendation_sessions for delete using (auth.uid() = user_id);

-- Gift products (from catalog generation)
create table if not exists public.gift_products (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.recommendation_sessions(id) on delete cascade not null,
  title text not null,
  description text,
  price numeric,
  url text not null,
  image_url text,
  retailer text,
  category text,
  is_selected boolean default false,
  ai_match_score numeric, -- How well it matches the profile
  ai_reasoning text, -- Why it was selected
  created_at timestamp with time zone default now()
);

alter table public.gift_products enable row level security;

create policy "products_select_own" on public.gift_products 
  for select using (
    auth.uid() = (
      select user_id from public.recommendation_sessions 
      where id = session_id
    )
  );

-- Bespoke packages
create table if not exists public.bespoke_packages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.recommendation_sessions(id) on delete cascade not null,
  title text not null,
  description text not null,
  total_price numeric,
  components jsonb default '[]'::jsonb, -- Array of items/experiences in the package
  personalization_details text, -- How it's customized for the recipient
  local_experiences jsonb default '[]'::jsonb, -- Location-specific suggestions
  created_at timestamp with time zone default now()
);

alter table public.bespoke_packages enable row level security;

create policy "packages_select_own" on public.bespoke_packages 
  for select using (
    auth.uid() = (
      select user_id from public.recommendation_sessions 
      where id = session_id
    )
  );

-- Purchases/transactions
create table if not exists public.purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  stripe_payment_intent_id text,
  stripe_subscription_id text,
  amount numeric not null,
  currency text default 'usd',
  purchase_type text check (purchase_type in ('credits', 'subscription', 'one_time')),
  credits_purchased integer,
  status text default 'pending' check (status in ('pending', 'completed', 'failed', 'refunded')),
  created_at timestamp with time zone default now()
);

alter table public.purchases enable row level security;

create policy "purchases_select_own" on public.purchases for select using (auth.uid() = user_id);
create policy "purchases_insert_own" on public.purchases for insert with check (auth.uid() = user_id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', null)
  )
  on conflict (id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute function public.handle_new_user();

-- Update timestamp function
create or replace function public.handle_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Triggers for updated_at
create trigger profiles_updated_at before update on public.profiles
  for each row execute function public.handle_updated_at();

create trigger social_profiles_updated_at before update on public.social_profiles
  for each row execute function public.handle_updated_at();
