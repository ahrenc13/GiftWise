-- Viral Features & Referral System

-- Add referral tracking to profiles
alter table profiles add column if not exists referral_code text unique;
alter table profiles add column if not exists referred_by uuid references profiles(id);
alter table profiles add column if not exists total_referrals integer default 0;
alter table profiles add column if not exists referral_credits numeric default 0;
alter table profiles add column if not exists referral_tier text default 'bronze';

-- Shareable wishlists/recommendations
create table if not exists shared_recommendations (
  id uuid primary key default gen_random_uuid(),
  share_id text unique not null,
  user_id uuid references profiles(id) on delete cascade not null,
  session_id uuid references recommendation_sessions(id) on delete cascade not null,
  is_public boolean default true,
  views integer default 0,
  clicks integer default 0,
  conversions integer default 0,
  created_at timestamptz default now(),
  expires_at timestamptz
);

alter table shared_recommendations enable row level security;

create policy "Anyone can view public shares" on shared_recommendations for select using (is_public = true);
create policy "Users can manage own shares" on shared_recommendations for all using (auth.uid() = user_id);

-- Track share clicks/views
create table if not exists share_events (
  id uuid primary key default gen_random_uuid(),
  share_id text not null,
  event_type text not null, -- 'view', 'click', 'conversion'
  product_index integer,
  referrer_url text,
  ip_address text,
  user_agent text,
  created_at timestamptz default now()
);

alter table share_events enable row level security;

create policy "Anyone can create share events" on share_events for insert with check (true);

-- Referral tracking
create table if not exists referrals (
  id uuid primary key default gen_random_uuid(),
  referrer_id uuid references profiles(id) on delete cascade not null,
  referred_user_id uuid references profiles(id) on delete cascade not null,
  referral_code text not null,
  status text default 'pending', -- pending, completed, rewarded
  credit_awarded numeric default 0,
  created_at timestamptz default now(),
  completed_at timestamptz,
  unique(referred_user_id)
);

alter table referrals enable row level security;

create policy "Users can view own referrals" on referrals for select using (auth.uid() = referrer_id or auth.uid() = referred_user_id);

-- Function to generate unique referral code
create or replace function generate_referral_code(user_email text)
returns text
language plpgsql
as $$
declare
  code_base text;
  hash_val text;
  final_code text;
begin
  -- Create hash from email
  hash_val := encode(digest(user_email, 'md5'), 'hex');
  -- Take first 4 chars and make uppercase
  code_base := upper(substring(hash_val, 1, 4));
  -- Prepend GIFT
  final_code := 'GIFT' || code_base;
  return final_code;
end;
$$;

-- Function to award referral credits
create or replace function award_referral_credits()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  referrer_id uuid;
  credit_amount numeric := 5.00;
begin
  -- Find the referrer
  select id into referrer_id
  from public.profiles
  where referral_code = new.referred_by_code
  limit 1;

  if referrer_id is not null then
    -- Award credits to referrer
    update public.profiles
    set 
      referral_credits = referral_credits + credit_amount,
      total_referrals = total_referrals + 1,
      referral_tier = case
        when total_referrals + 1 >= 50 then 'platinum'
        when total_referrals + 1 >= 20 then 'gold'
        when total_referrals + 1 >= 5 then 'silver'
        else 'bronze'
      end
    where id = referrer_id;

    -- Record the referral
    insert into public.referrals (referrer_id, referred_user_id, referral_code, status, credit_awarded)
    values (referrer_id, new.id, new.referred_by_code, 'completed', credit_amount);
  end if;

  return new;
end;
$$;

-- Create indexes for performance
create index if not exists idx_shared_recommendations_share_id on shared_recommendations(share_id);
create index if not exists idx_profiles_referral_code on profiles(referral_code);
create index if not exists idx_referrals_referrer on referrals(referrer_id);
create index if not exists idx_share_events_share_id on share_events(share_id);
