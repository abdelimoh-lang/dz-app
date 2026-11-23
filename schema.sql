-- مخطط تطبيق منصة التاجر الجزائري (جداول بادئتها dz_ لتفادي التعارض مع جداول أخرى)

create table if not exists public.dz_products (
  id bigint generated always as identity primary key,
  name text not null unique,
  quantity integer not null default 0,
  buy_price integer not null default 0,
  sell_price integer not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.dz_orders (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  customer text not null,
  phone text not null,
  wilaya text not null,
  product text not null,
  amount integer not null default 0,
  shipping integer not null default 0,
  buy_cost integer not null default 0,
  status text not null default 'pending'
    check (status in ('pending', 'delivered', 'returned'))
);

create index if not exists dz_orders_status_idx on public.dz_orders (status);
create index if not exists dz_orders_created_idx on public.dz_orders (created_at desc);

-- RLS مفعّل بلا سياسات للمفاتيح العامة: الوصول يتم فقط بمفتاح الخدمة من خادم Streamlit.
alter table public.dz_products enable row level security;
alter table public.dz_orders enable row level security;

-- دالة ذرّية لتعديل المخزون (تُستدعى من الخادم فقط)
create or replace function public.dz_adjust_stock(p_name text, p_delta integer)
returns void
language sql
security invoker
set search_path = public
as $$
  update public.dz_products set quantity = quantity + p_delta where name = p_name;
$$;
revoke execute on function public.dz_adjust_stock(text, integer) from public, anon, authenticated;
