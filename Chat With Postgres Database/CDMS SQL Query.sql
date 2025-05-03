-- Cleaned ERD-generated SQL script
-- Removed MATCH SIMPLE because it's the default for single-column foreign keys
-- Removed NOT VALID to ensure full validation of foreign key constraints
-- Generated via pgAdmin 4 ERD tool

BEGIN;


CREATE TABLE IF NOT EXISTS public.cars
(
    car_id bigserial NOT NULL,
	year smallint,
    make text,
    model text,
	trim text,
	body text,
	transmission text,
	vin text,
	mileage integer,
    color text,
	interior text,
	price numeric,
    selling_price numeric,
    CONSTRAINT pk_cars PRIMARY KEY (car_id),
    CONSTRAINT unique_cars_vin UNIQUE (vin)
);

CREATE TABLE IF NOT EXISTS public.sales	
(
    sale_id bigserial NOT NULL,
    sale_date date,
    sale_price numeric,
    payment_method text,
    customer_id integer,
    car_id integer,
    employee_id integer,
    CONSTRAINT pk_sales PRIMARY KEY (sale_id)
);

CREATE TABLE IF NOT EXISTS public.customers
(
    customer_id bigserial NOT NULL,
    first_name text,
    last_name text,
    address text,
    phone_number text,
    email text,
    dob text,
    gender text,
    CONSTRAINT pk_customers PRIMARY KEY (customer_id),
    CONSTRAINT unique_customers_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS public.employees
(
    employee_id bigserial NOT NULL,
    first_name text,
    last_name text,
    "position" text,
    phone_number text,
    email text,
    department text,
    hire_date date,
    salary numeric,
    CONSTRAINT pk_employees PRIMARY KEY (employee_id),
    CONSTRAINT unique_employees_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS public.service
(
    service_id bigserial NOT NULL,
    service_type text,
    service_date date,
    service_cost numeric,
    car_id integer,
    employee_id integer,
    CONSTRAINT pk_service PRIMARY KEY (service_id)
);

ALTER TABLE IF EXISTS public.sales
    ADD CONSTRAINT fk_sales_customer FOREIGN KEY (customer_id)
    REFERENCES public.customers (customer_id)
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
	

ALTER TABLE IF EXISTS public.sales
    ADD CONSTRAINT fk_sales_employee FOREIGN KEY (employee_id)
    REFERENCES public.employees (employee_id)
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS public.sales
    ADD CONSTRAINT fk_sales_car FOREIGN KEY (car_id)
    REFERENCES public.cars (car_id)
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS public.service
    ADD CONSTRAINT fk_service_employee FOREIGN KEY (employee_id)
    REFERENCES public.employees (employee_id)
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS public.service
    ADD CONSTRAINT fk_service_car FOREIGN KEY (car_id)
    REFERENCES public.cars (car_id)
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;

END;

SELECT * FROM cars
SELECT * FROM customers
SELECT * FROM employees
SELECT * FROM sales
SELECT * FROM service

COPY cars(year, make, model, trim, body, transmission, vin, mileage, color, interior, price, selling_price)
FROM 'D:\Freelancing Projects\Mahran tasks\code\database\Cars.csv'
DELIMITER ','
CSV HEADER;

COPY customers(first_name, last_name, address, phone_number, email, dob, gender)
FROM 'D:\Freelancing Projects\Mahran tasks\code\database\Customers.csv'
DELIMITER ','
CSV HEADER;

COPY employees(first_name, last_name, position, phone_number, email, department, hire_date, salary)
FROM 'D:\Freelancing Projects\Mahran tasks\code\database\Employees.csv'
DELIMITER ','
CSV HEADER;

COPY sales(sale_date, sale_price, payment_method, customer_id, car_id, employee_id)
FROM 'D:\Freelancing Projects\Mahran tasks\code\database\Sales.csv'
DELIMITER ','
CSV HEADER;

COPY service(service_type, service_date, service_cost, car_id, employee_id)
FROM 'D:\Freelancing Projects\Mahran tasks\code\database\Service.csv'
DELIMITER ','
CSV HEADER;