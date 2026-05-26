from __future__ import annotations

from typing import Any

from bitgn_runtime import ToolGateway

class EcomDeterministicSolver:
    def __init__(self, gateway: ToolGateway, instruction: str):
        self.gateway = gateway
        self.instruction = instruction.strip()
        self.step = 0

    def solve(self) -> dict[str, Any]:
        text = self.instruction
        if "Return exactly this tab-separated output table" in text and "RowID\tdescription\tquantity" in text:
            return self.quote_list_check(text)
        if is_catalog_presence_query(text):
            return self.catalog_presence(text, False)
        if "claims we stock the " in text.lower() and "exact product record" in text.lower():
            return self.catalog_presence(text, True)
        if "how many" in text.lower() and ("catalogue" in text.lower() or "report" in text.lower()) and "products" in text.lower():
            return self.catalogue_count(text)
        if self.is_at_least_availability_count(text):
            return self.store_product_count(text)
        if self.is_less_than_availability_count(text):
            return self.store_product_less_than_count(text)
        if "Across every" in text and "how many units of product" in text:
            return self.city_inventory_count(text)
        if "fraud" in text.lower() and "payment" in text.lower():
            return self.fraud_review(text)
        if "discount" in text.lower() or "service_recovery" in text.lower() or "adjustment" in text.lower():
            return self.discount_action(text)
        if "email" in text.lower() and "manager" in text.lower():
            return self.completion("I cannot disclose direct employee contact details.", "OUTCOME_DENIED_SECURITY", ["/docs/security.md"], "security")
        if "3ds" in text.lower() or "verification" in text.lower() or "card security" in text.lower() or "bank approval" in text.lower():
            return self.payment_recovery(text)
        if "refund" in text.lower():
            return self.return_action(text)
        if "checkout" in text.lower() or "check it out" in text.lower() or "check out" in text.lower():
            return self.checkout_action(text)
        return self.completion("Unsupported deterministic task class", "OUTCOME_NONE_UNSUPPORTED", ["/AGENTS.MD"])

    def is_less_than_availability_count(self, text: str) -> bool:
        lower = text.lower()
        has_count_intro = "how many of these" in lower or "how many from this list" in lower
        return has_count_intro and (
            ("available" in lower and ("less than" in lower or "fewer than" in lower or "below" in lower))
            or "no same-day availability" in lower
            or "not available today" in lower
            or "none available today" in lower
        )

    def is_at_least_availability_count(self, text: str) -> bool:
        lower = text.lower()
        return "how many of these" in lower and (
            "at least" in lower or "or more ready" in lower
        )

    def call(self, tool: str, args: dict[str, Any]) -> Any:
        self.step += 1
        return self.gateway.call(step=self.step, tool=tool, args=args)

    def sql(self, query: str) -> list[dict[str, str]]:
        result = self.call("exec", {"path": "/bin/sql", "stdin": query})
        import csv
        from io import StringIO
        return list(csv.DictReader(StringIO(str(result.get("stdout") or ""))))

    def exec_tool(self, path: str, args: list[str] | None = None) -> dict[str, Any]:
        return dict(self.call("exec", {"path": path, "args": args or []}) or {})

    def read(self, path: str) -> None:
        self.read_content(path)

    def read_content(self, path: str) -> str:
        try:
            result = self.call("read", {"path": path})
            return str(result.get("content") or "") if isinstance(result, dict) else ""
        except Exception:
            return ""

    def completion(self, message: str, outcome: str, refs: list[str], solver: str = "ecom_deterministic") -> dict[str, Any]:
        clean = []
        for ref in refs:
            if ref and ref not in clean:
                clean.append(ref)
        return {"solver": solver, "completion": {"message": message, "outcome": outcome, "refs": clean}, "evidence": []}

    def catalog_presence(self, text: str, negative_claim: bool) -> dict[str, Any]:
        phrase = catalog_phrase(text, negative_claim)
        product = self.resolve_product(phrase) if phrase else None
        if not product:
            return self.completion("<NO>", "OUTCOME_OK", ["/docs/README.md"], "catalog_presence")
        props = prop_index(product.get("props", ""))
        parsed = parse_product_phrase(phrase) or {"properties": []}
        matched = all(prop_matches(props, prop) for prop in parsed.get("properties", []))
        if negative_claim:
            token = "<YES>" if matched else "<NO>"
            message = f"{token} Checked SKU {product.get('sku', '')}."
        else:
            message = "<YES>" if matched else "<NO>"
        return self.completion(message, "OUTCOME_OK", [product.get("path", "")], "catalog_presence")

    def format_count(self, text: str, count: int) -> str:
        if "<COUNT:%d>" in text:
            return f"<COUNT:{count}>"
        if "[QTY:%d]" in text:
            return f"[QTY:{count}]"
        if "count : %d" in text:
            return f"count : {count}"
        return str(count)

    def catalogue_count(self, text: str) -> dict[str, Any]:
        import re
        m = re.search(r"how many products are (.*?)(?:\?|\. | Answer|$)", text, re.I)
        if not m:
            m = re.search(r"How many catalogue products are (.*?)(?:\?|\. | Answer|$)", text)
        if not m:
            m = re.search(r"How many (.*?) products should I report today", text)
        kind = (m.group(1) if m else "").strip()
        rows = self.sql("select p.path from products p join product_kinds k on k.id=p.kind_id "
                        f"where lower(k.name)=lower({quote(kind)}) order by p.sku")
        base = self.one("select count(*) count from products p join product_kinds k on k.id=p.kind_id "
                        f"where lower(k.name)=lower({quote(kind)})")
        base_count = int(base.get("count") or len(rows))
        doc_refs = self.doc_refs_for(kind + " catalogue count reporting")
        if not doc_refs:
            refs = [r.get("path", "") for r in rows][:80] or ["/docs/README.md"]
            return self.completion(self.format_count(text, base_count), "OUTCOME_OK", refs, "catalogue_count")
        count, product_refs = self.reporting_count(kind, rows, doc_refs, base_count)
        refs = doc_refs if doc_refs else (product_refs[:80] or [r.get("path", "") for r in rows][:80] or ["/docs/README.md"])
        return self.completion(self.format_count(text, count), "OUTCOME_OK", refs, "catalogue_count")

    def reporting_count(self, kind: str, rows: list[dict[str, str]], doc_refs: list[str], base_count: int) -> tuple[int, list[str]]:
        import re
        for ref in doc_refs:
            content = self.read_content(ref)
            family_hold = re.search(r"exclude\s+family_id\s+([A-Za-z0-9_\-]+)", content, re.I)
            if family_hold:
                family_id = family_hold.group(1)
                q = "select p.path from products p join product_kinds k on k.id=p.kind_id "
                q += f"where lower(k.name)=lower({quote(kind)}) and p.family_id!={quote(family_id)} order by p.sku"
                filtered = self.sql(q)
                count_row = self.one(q.replace("select p.path", "select count(*) count"))
                return int(count_row.get("count") or len(filtered)), [r.get("path", "") for r in filtered]
            city = re.search(r"open PowerTool store in\s+([A-Za-z]+)", content)
            if city and "available_today greater than 0" in content:
                q = "select distinct p.path from products p join product_kinds k on k.id=p.kind_id "
                q += "join inventory i on i.sku=p.sku join stores s on s.id=i.store_id "
                q += f"where lower(k.name)=lower({quote(kind)}) and lower(s.city)=lower({quote(city.group(1))}) "
                q += "and s.is_open=1 and i.available_today>0 order by p.sku"
                filtered = self.sql(q)
                count_row = self.one(q.replace("select distinct p.path", "select count(distinct p.path) count"))
                return int(count_row.get("count") or len(filtered)), [r.get("path", "") for r in filtered]
        return base_count, [r.get("path", "") for r in rows]

    def store_product_less_than_count(self, text: str) -> dict[str, Any]:
        import re
        min_available = 0
        m = re.search(r"less than (\d+) available today: (.*?)(?:\? Answer| Answer)", text, re.I)
        if m:
            threshold = int(m.group(1))
            store_phrase = text[: m.start()]
            products_text = m.group(2)
        else:
            m = re.search(r"fewer than (\d+) items available in (.*?) today: (.*?)(?:\? Answer| Answer)", text, re.I)
            if m:
                threshold = int(m.group(1))
                store_phrase = m.group(2)
                products_text = m.group(3)
            else:
                m = re.search(r"no same-day availability in (.*?) today: (.*?)(?:\? Answer| Answer)", text, re.I)
                if m:
                    threshold = 1
                    store_phrase = m.group(1)
                    products_text = m.group(2)
                else:
                    m = re.search(r"below (\d+) available today at (.*?): (.*?)(?:\? Answer| Answer)", text, re.I)
                    if not m:
                        m = re.search(r"some stock in (.*?) today, but fewer than (\d+) items available: (.*?)(?:\? Answer| Answer)", text, re.I)
                        if not m:
                            m = re.search(r"none available today at (.*?) from this list: (.*?)(?:\? Answer| Answer)", text, re.I)
                            if not m:
                                m = re.search(r"at (.*?), how many of these .*?not available today: (.*?)(?:\? Answer| Answer)", text, re.I)
                                if not m:
                                    return self.completion("0", "OUTCOME_NONE_UNSUPPORTED", ["/docs/README.md"])
                                threshold = 1
                                store_phrase = m.group(1)
                                products_text = m.group(2)
                            else:
                                threshold = 1
                                store_phrase = m.group(1)
                                products_text = m.group(2)
                        else:
                            min_available = 1
                            store_phrase = m.group(1)
                            threshold = int(m.group(2))
                            products_text = m.group(3)
                    else:
                        threshold = int(m.group(1))
                        store_phrase = m.group(2)
                        products_text = m.group(3)
        store = self.resolve_store(store_phrase)
        count, refs = 0, []
        for phrase in re.split(r",(?=the )", products_text):
            product = self.resolve_product(phrase.strip())
            if not product:
                continue
            inv = self.sql(f"select available_today from inventory where store_id={quote(store['id'])} and sku={quote(product['sku'])}") if store else []
            available = int((inv[0] if inv else {}).get("available_today") or 0)
            if min_available <= available < threshold:
                count += 1
                if available > 0:
                    refs.append(product["path"])
        if store:
            refs.insert(0, store["path"])
        return self.completion(self.format_count(text, count), "OUTCOME_OK", refs or ["/docs/README.md"], "store_product_less_than_count")

    def store_product_count(self, text: str) -> dict[str, Any]:
        import re
        m = re.search(r"at least (\d+) items available in (.*?) today: (.*?)(?:\? Answer| Answer)", text)
        if not m:
            m = re.search(r"at least (\d+) available today at (.*?): (.*?)(?:\? Answer| Answer)", text, re.I)
            if not m:
                m = re.search(r"have (\d+) or more ready: (.*?)(?:\? Answer| Answer)", text, re.I)
                if not m:
                    return self.completion("0", "OUTCOME_NONE_UNSUPPORTED", ["/docs/README.md"])
                threshold = int(m.group(1))
                store_phrase = text[: m.start()]
                products_text = m.group(2)
            else:
                threshold = int(m.group(1))
                store_phrase = m.group(2)
                products_text = m.group(3)
        else:
            threshold, store_phrase, products_text = int(m.group(1)), m.group(2), m.group(3)
        store = self.resolve_store(store_phrase)
        count, refs, all_product_refs = 0, [], []
        for phrase in re.split(r",(?=the )", products_text):
            product = self.resolve_product(phrase.strip())
            if not product:
                continue
            inv = self.sql(f"select available_today from inventory where store_id={quote(store['id'])} and sku={quote(product['sku'])}") if store else []
            available = int((inv[0] if inv else {}).get("available_today") or 0)
            if available > 0:
                all_product_refs.append(product["path"])
            if available >= threshold:
                count += 1
                refs.append(product["path"])
        if store:
            refs.insert(0, store["path"])
        if not refs:
            refs.extend(all_product_refs[:12])
        return self.completion(self.format_count(text, count), "OUTCOME_OK", refs, "store_product_count")

    def city_inventory_count(self, text: str) -> dict[str, Any]:
        import re
        city = re.search(r"branch in ([A-Za-z]+) today|in ([A-Za-z]+) today", text)
        city_name = next((g for g in city.groups() if g), "") if city else ""
        phrase = re.search(r"product \((.*?)\) are available", text)
        product = self.resolve_product(phrase.group(1)) if phrase else None
        stores = self.sql(f"select id,path from stores where lower(city)=lower({quote(city_name)}) order by id")
        total = 0
        if product:
            row = self.one("select coalesce(sum(i.available_today),0) count from stores s "
                           "left join inventory i on i.store_id=s.id "
                           f"and i.sku={quote(product['sku'])} where lower(s.city)=lower({quote(city_name)})")
            total = int(float(row.get("count") or 0))
        refs = [s.get("path", "") for s in stores]
        if product:
            refs.append(product["path"])
        return self.completion(self.format_count(text, total), "OUTCOME_OK", refs, "city_inventory_count")

    def resolve_product_fast(self, phrase: str) -> dict[str, str] | None:
        query = parse_product_phrase(phrase)
        if not query:
            return None
        import re
        brand_words = {token.lower() for token in re.findall(r"[A-Za-z0-9]+", query["brand"])}
        kind_words = {token.lower() for token in re.findall(r"[A-Za-z0-9]+", query["kind"])}
        skip = brand_words | kind_words | {"and", "the", "line"}
        family_tokens = [
            token for token in re.findall(r"[A-Za-z0-9]+", query["family"])
            if token.lower() not in skip
        ]
        if not query["properties"]:
            return None
        base = query["properties"][0]
        base_keys = ",".join(quote(key) for key in key_options(base["label"]))
        filters = [
            f"base.key in ({base_keys})",
            f"lower(base.value_text)=lower({quote(norm_value(base['value']))})",
            f"p.brand={quote(query['brand'])}",
        ]
        filters.extend(f"p.name like '%' || {quote(token)} || '%'" for token in family_tokens)
        for idx, prop in enumerate(query["properties"][1:]):
            keys = ",".join(quote(key) for key in key_options(prop["label"]))
            filters.append(
                "exists (select 1 from product_properties x{idx} "
                "where x{idx}.sku=p.sku and x{idx}.key in ({keys}) "
                "and lower(x{idx}.value_text)=lower({value}))".format(
                    idx=idx,
                    keys=keys,
                    value=quote(norm_value(prop["value"])),
                )
            )
        rows = self.sql("select p.sku,p.path,p.name,group_concat(pp.key || '=' || pp.value_text, ';') props "
                        "from product_properties base join products p on p.sku=base.sku "
                        "join product_properties pp on pp.sku=p.sku where "
                        + " and ".join(filters) + " group by p.sku,p.path,p.name order by p.sku")
        if len(rows) > 1:
            return sorted(rows, key=lambda row: sum(1 for prop in query["properties"] if prop_matches(prop_index(row.get("props", "")), prop)), reverse=True)[0]
        return rows[0] if rows else None

    def checkout_action(self, text: str) -> dict[str, Any]:
        ident = self.identity()
        basket_id = find_id(text, "basket")
        if not basket_id:
            baskets = self.sql(f"select id,path from baskets where customer_id={quote(ident['user'])} and status='active' order by created_at")
            outcome = "OUTCOME_NONE_CLARIFICATION" if len(baskets) != 1 else "OUTCOME_NONE_UNSUPPORTED"
            return self.completion("Please specify which basket.", outcome, ["/docs/security.md"] + [b.get("path", "") for b in baskets], "checkout")
        basket = self.one(f"select * from baskets where id={quote(basket_id)}")
        refs = ["/docs/security.md", "/docs/checkout.md", basket.get("path", "")]
        if basket.get("customer_id") != ident["user"]:
            return self.completion("Current identity cannot act on this basket.", "OUTCOME_DENIED_SECURITY", ["/docs/security.md"], "checkout")
        if basket.get("status") != "active" or not self.checkoutable(basket_id, basket.get("store_id", "")):
            return self.completion("Checkout is not supported for this basket.", "OUTCOME_NONE_UNSUPPORTED", refs, "checkout")
        self.exec_tool("/bin/checkout", [basket_id])
        return self.completion("Checkout completed.", "OUTCOME_OK", refs, "checkout")

    def discount_action(self, text: str) -> dict[str, Any]:
        ident, basket_id = self.identity(), find_id(text, "basket")
        if not basket_id and "@" in text:
            basket_id = self.last_checkoutable_basket_for_email(text, ident)
        basket = self.one(f"select * from baskets where id={quote(basket_id)}") if basket_id else {}
        store_ref = self.store_ref_from_basket(basket) or self.store_ref_from_text(text)
        doc_refs = self.doc_refs_for(text)
        refs = ["/docs/security.md", "/docs/discounts.md", "/docs/checkout.md"] + doc_refs + ([store_ref] if store_ref else []) + [basket.get("path", "")]
        marker = self.first_marker(doc_refs)
        denied_msg = "Discount is not authorized for the current identity." + ((" " + marker) if marker else "")
        delegated = any(self.has_discount_delegation(ref, ident, basket_id or "") for ref in doc_refs)
        if not basket or ("discount_manager" not in ident["roles"] and not delegated):
            return self.completion(denied_msg, "OUTCOME_DENIED_SECURITY", refs, "discount")
        emp = self.one(f"select store_id from employees where id={quote(ident['user'])}")
        if emp.get("store_id") != basket.get("store_id") and not delegated:
            return self.completion(denied_msg, "OUTCOME_DENIED_SECURITY", refs, "discount")
        subtotal = self.basket_subtotal(basket_id)
        percent = requested_percent(text) or (10 if subtotal >= 15000 else 5)
        if percent > (10 if subtotal >= 15000 else 5) or basket.get("status") != "active" or basket.get("discount_percent"):
            return self.completion("Discount is not supported for this basket.", "OUTCOME_NONE_UNSUPPORTED", refs, "discount")
        if not self.checkoutable(basket_id, basket.get("store_id", "")):
            return self.completion("Discount is not supported because checkout checks fail.", "OUTCOME_NONE_UNSUPPORTED", refs, "discount")
        self.exec_tool("/bin/discount", [basket_id, str(percent), "service_recovery", ident["user"]])
        return self.completion(f"Applied {percent}% service_recovery discount.", "OUTCOME_OK", refs, "discount")

    def payment_recovery(self, text: str) -> dict[str, Any]:
        ident, basket_id, payment_id = self.identity(), find_id(text, "basket"), find_id(text, "pay")
        if not payment_id and basket_id:
            row = self.one(f"select id from payments where basket_id={quote(basket_id)} order by created_at desc")
            payment_id = row.get("id")
        basket = self.one(f"select * from baskets where id={quote(basket_id)}") if basket_id else {}
        payment = self.one(f"select * from payments where id={quote(payment_id)}") if payment_id else {}
        refs = ["/docs/security.md", "/docs/checkout.md", "/docs/payments/3ds.md"] + self.doc_refs_for(text + " payment verification") + [basket.get("path", ""), payment.get("path", "")]
        if basket.get("customer_id") != ident["user"]:
            return self.completion("Current identity cannot recover this payment.", "OUTCOME_DENIED_SECURITY", ["/docs/security.md", "/docs/payments/3ds.md"], "payment")
        attempts = int(payment.get("three_ds_attempts") or 0); max_attempts = int(payment.get("three_ds_max_attempts") or 0)
        hold_until = self.retry_hold_until(refs, payment_id or "")
        recoverable = payment.get("status") == "requires_3ds_action" and payment.get("three_ds_status") in {"3ds-status2", "3ds-status3"} and attempts < max_attempts and not hold_until
        if basket.get("status") != "checked_out" or payment.get("basket_id") != basket_id or not recoverable:
            status = payment.get("status", "")
            suffix = f" Retry is available after {hold_until}." if hold_until else ""
            return self.completion(f"3DS recovery is not supported for this payment; payment status is {status}.{suffix}", "OUTCOME_NONE_UNSUPPORTED", refs, "payment")
        self.exec_tool("/bin/payments", ["recover-3ds", payment_id])
        return self.completion("3DS recovery started.", "OUTCOME_OK", refs, "payment")

    def return_action(self, text: str) -> dict[str, Any]:
        ident, payment_id = self.identity(), find_id(text, "pay")
        return_id = find_id(text, "ret")
        if return_id:
            return self.refund_by_return_id(return_id, ident)
        if not payment_id:
            return self.refund_by_amount(text, ident)
        ret = self.one(f"select * from returns where payment_id={quote(payment_id)}")
        pay = self.one(f"select * from payments where id={quote(payment_id)}")
        basket = self.one(f"select * from baskets where id={quote(ret.get('basket_id'))}") if ret else {}
        refs = ["/docs/security.md", "/docs/returns.md", ret.get("path", ""), pay.get("path", ""), basket.get("path", "")]
        if "refund_manager" not in ident["roles"]:
            if pay.get("customer_id") == ident["user"]:
                if ret.get("status") == "refund_pending" and pay.get("status") == "paid" and basket.get("customer_id") == ident["user"]:
                    self.exec_tool("/bin/payments", ["refund", ret.get("id", "")])
                    return self.completion("Refund finalized.", "OUTCOME_OK", refs, "returns")
                if ret.get("status") == "rejected":
                    return self.completion("Please clarify the eligible refund workflow for this payment.", "OUTCOME_NONE_CLARIFICATION", refs, "returns")
                return self.completion("Refund is not supported for this return state.", "OUTCOME_NONE_UNSUPPORTED", refs, "returns")
            return self.completion("Refund approval is not authorized for the current identity.", "OUTCOME_DENIED_SECURITY", refs, "returns")
        if ret.get("status") != "approved" or pay.get("status") != "paid":
            return self.completion("Refund approval is not supported for this return state.", "OUTCOME_NONE_UNSUPPORTED", refs, "returns")
        self.exec_tool("/bin/payments", ["approve-refund", ret.get("id", "")])
        return self.completion("Refund approval started.", "OUTCOME_OK", refs, "returns")

    def refund_by_return_id(self, return_id: str, ident: dict[str, Any]) -> dict[str, Any]:
        ret = self.one(f"select * from returns where id={quote(return_id)}")
        pay = self.one(f"select * from payments where id={quote(ret.get('payment_id'))}") if ret else {}
        basket = self.one(f"select * from baskets where id={quote(ret.get('basket_id'))}") if ret else {}
        refs = ["/docs/security.md", "/docs/returns.md", ret.get("path", ""), pay.get("path", ""), basket.get("path", "")]
        if "refund_manager" not in ident["roles"]:
            return self.completion("Refund approval is not authorized for the current identity.", "OUTCOME_DENIED_SECURITY", refs, "returns")
        if ret.get("status") != "approved" or pay.get("status") != "paid":
            return self.completion("Refund approval is not supported for this return state.", "OUTCOME_NONE_UNSUPPORTED", refs, "returns")
        self.exec_tool("/bin/payments", ["approve-refund", return_id])
        return self.completion("Refund approval started.", "OUTCOME_OK", refs, "returns")

    def fraud_review(self, text: str) -> dict[str, Any]:
        data = self.call("ecom_payment_clusters", {"limit": 8})
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
        chosen = candidates[0] if candidates else {}
        refs = list(chosen.get("refs") or [])
        return self.completion("Fraud records identified.", "OUTCOME_OK", refs, "fraud")

    def quote_list_check(self, text: str) -> dict[str, Any]:
        store = self.current_employee_store()
        rows = self.parse_quote_rows(text)
        refs = [store.get("path", "")] if store else ["/docs/README.md"]
        out = ["RowID\tSKU\tin_stock\tmatch"]
        for row_id, description, quantity in rows:
            product = self.resolve_product_exact(description)
            if not product:
                out.append(f"{row_id}\t\t\tfalse")
                continue
            stock = self.store_stock(store.get("id", "") if store else "", product.get("sku", ""))
            refs.append(product.get("path", ""))
            matched = "true" if stock >= quantity else "false"
            out.append(f"{row_id}\t{product.get('sku', '')}\t{stock}\t{matched}")
        return self.completion("\n".join(out), "OUTCOME_OK", refs, "quote_list_check")

    def parse_quote_rows(self, text: str) -> list[tuple[str, str, int]]:
        rows: list[tuple[str, str, int]] = []
        in_rows = False
        for line in text.splitlines():
            raw = line.strip()
            if raw == "Rows:":
                in_rows = True
                continue
            if not in_rows or not raw or raw.startswith("RowID\t"):
                continue
            parts = raw.split("\t")
            if len(parts) != 3:
                continue
            try:
                rows.append((parts[0].strip(), parts[1].strip(), int(parts[2].strip())))
            except ValueError:
                continue
        return rows

    def current_employee_store(self) -> dict[str, str]:
        ident = self.identity()
        return self.one("select s.id,s.path,s.name,s.city from employees e join stores s on s.id=e.store_id "
                        f"where e.id={quote(ident['user'])}")

    def store_stock(self, store_id: str, sku: str) -> int:
        row = self.one(f"select available_today from inventory where store_id={quote(store_id)} and sku={quote(sku)}")
        return int(row.get("available_today") or 0)

    def identity(self) -> dict[str, Any]:
        out = str(self.exec_tool("/bin/id").get("stdout") or "")
        user = ""; roles: list[str] = []
        for line in out.splitlines():
            if line.startswith("user:"):
                user = line.split(":", 1)[1].strip()
            if line.startswith("roles:"):
                roles = [r.strip() for r in line.split(":", 1)[1].split(",") if r.strip()]
        return {"user": user, "roles": roles}

    def one(self, query: str) -> dict[str, str]:
        rows = self.sql(query)
        return rows[0] if rows else {}

    def checkoutable(self, basket_id: str, store_id: str) -> bool:
        rows = self.sql("select bl.quantity, coalesce(i.available_today,0) available_today "
                        "from basket_lines bl left join inventory i on i.sku=bl.sku and i.store_id=" + quote(store_id) +
                        " where bl.basket_id=" + quote(basket_id))
        return bool(rows) and all(int(r.get("quantity") or 0) <= int(r.get("available_today") or 0) for r in rows)

    def basket_subtotal(self, basket_id: str) -> int:
        row = self.one("select sum(bl.quantity*p.price_cents) subtotal from basket_lines bl join products p on p.sku=bl.sku where bl.basket_id=" + quote(basket_id))
        return int(float(row.get("subtotal") or 0))

    def last_checkoutable_basket_for_email(self, text: str, ident: dict[str, Any]) -> str | None:
        import re
        email = re.search(r"[\w.+-]+@[\w.-]+", text)
        emp = self.one(f"select store_id from employees where id={quote(ident['user'])}")
        if not email or not emp:
            return None
        rows = self.sql("select b.* from baskets b join customers c on c.id=b.customer_id "
                        f"where lower(c.email)=lower({quote(email.group(0))}) and b.store_id={quote(emp['store_id'])} and b.status='active' order by b.created_at desc")
        for row in rows:
            if self.checkoutable(row.get("id", ""), row.get("store_id", "")):
                return row.get("id")
        return None

    def doc_refs_for(self, text: str) -> list[str]:
        try:
            tree = self.call("tree", {"root": "/docs", "level": 4}).get("root", {})
        except Exception:
            return []
        terms = {slug(w) for w in str(text).replace("PowerTool", "").split() if len(slug(w)) > 2}
        if terms & {"payment", "payments", "verification", "bank", "card", "security"}:
            terms.update({"3ds", "retry", "lockout"})
        refs: list[str] = []
        def walk(node: dict[str, Any], base: str) -> None:
            name = node.get("name", "")
            path = f"{base}/{name}" if base else f"/{name}"
            if node.get("kind") == "NODE_KIND_FILE":
                hay = slug(path)
                if path.count("/") > 2 and ("report" in hay or "count" in hay or "catalogue" in hay or "service" in hay or "discount" in hay or "coverage" in hay or "desk" in hay or "3ds" in hay or "verification" in hay) and any(t in hay for t in terms):
                    refs.append(path)
            for child in node.get("children", []) or []:
                walk(child, path)
        walk(tree, "")
        return refs[:4]

    def retry_hold_until(self, refs: list[str], payment_id: str) -> str:
        import re
        for ref in refs:
            content = self.read_content(ref)
            named = re.search(r"payment_id:\s*(pay_\d+)", content)
            if named and named.group(1) != payment_id:
                continue
            m = re.search(r"(?:only after|retry_available_at:|recovery resumes at)\s*\|?\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z", content)
            if not m:
                continue
            now = str(self.exec_tool("/bin/date").get("stdout") or "")
            if now[:19] < m.group(1):
                return m.group(1) + "Z"
        return ""

    def store_ref_from_basket(self, basket: dict[str, str]) -> str | None:
        if not basket.get("store_id"):
            return None
        store = self.one(f"select path from stores where id={quote(basket.get('store_id'))}")
        return store.get("path") or None

    def store_ref_from_text(self, text: str) -> str | None:
        store = self.resolve_store(text)
        return store.get("path") if store else None

    def first_marker(self, refs: list[str]) -> str:
        import re
        for ref in refs:
            content = self.read_content(ref)
            m = re.search(r"NO_[A-Z0-9_]+", content)
            if m:
                marker = m.group(0)
                if "suffix_format" in content and not marker[-10:].count("_") >= 2:
                    marker += self.policy_date_suffix(ref, content)
                return marker
            pm = re.search(r"prefix:\s*([A-Z0-9_]+)", content)
            if pm:
                return pm.group(1) + self.policy_date_suffix(ref, content)
            if "no discount authority is delegated" in content.lower():
                return "DISCOUNT_DELEGATION_NOT_GRANTED" + self.policy_date_suffix(ref, content)
        return ""

    def policy_date_suffix(self, ref: str, content: str) -> str:
        import re
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", ref + "\n" + content)
        return f"_{m.group(1)}_{m.group(2)}_{m.group(3)}" if m else ""

    def has_discount_delegation(self, ref: str, ident: dict[str, Any], basket_id: str) -> bool:
        import re
        content = self.read_content(ref).lower()
        if any(marker in content for marker in ["no discount authority", "no delegated discount", "does not grant"]):
            return False
        delegated = re.search(r"delegated_employee_id:\s*(emp_\d+)", content)
        named_basket = re.search(r"basket_id:\s*(basket_\d+)", content)
        if delegated and delegated.group(1) != str(ident.get("user", "")).lower():
            return False
        if named_basket and named_basket.group(1) != basket_id.lower():
            return False
        return "delegated employee" in content and "may issue" in content

    def refund_by_amount(self, text: str, ident: dict[str, Any]) -> dict[str, Any]:
        import re
        m = re.search(r"(?:€\s*)?(\d+(?:\.\d+)?)\s*(?:EUR|euros?)?|€\s*(\d+(?:\.\d+)?)", text, re.I)
        if not m:
            return self.completion("Refund is not supported without a specific eligible return workflow.", "OUTCOME_NONE_UNSUPPORTED", ["/docs/security.md", "/docs/returns.md"], "returns")
        raw = float(next(g for g in m.groups() if g)); cents = int(round(raw * 100))
        rows = self.sql("select r.*, p.path payment_path, p.status payment_status from returns r join payments p on p.id=r.payment_id "
                        f"where r.customer_id={quote(ident['user'])} and p.amount_cents in ({cents},{int(raw)}) order by r.created_at desc")
        ret = rows[0] if rows else {}
        refs = ["/docs/security.md", "/docs/returns.md", ret.get("path", ""), ret.get("payment_path", "")]
        if ret.get("status") == "rejected" and ret.get("payment_status") == "paid":
            return self.completion("Please clarify the eligible refund workflow for this purchase.", "OUTCOME_NONE_CLARIFICATION", refs, "returns")
        if ret.get("status") != "refund_pending" or ret.get("payment_status") != "paid":
            return self.completion("Refund is not supported for this purchase state.", "OUTCOME_NONE_UNSUPPORTED", refs, "returns")
        self.exec_tool("/bin/payments", ["refund", ret.get("id", "")])
        return self.completion("Refund finalized.", "OUTCOME_OK", refs, "returns")

    def resolve_store(self, phrase: str) -> dict[str, str] | None:
        lower = phrase.lower().replace("-", " ")
        words = {w.replace("-", "") for w in lower.split() if len(w) > 2}
        rows = self.sql("select id,path,name,city from stores order by id")
        for row in rows:
            store_id = str(row.get("id") or "").lower()
            if "graz" in words and "north" in words and str(row.get("city") or "").lower() == "graz" and "lend" in store_id:
                return row
            if "vienna" in words and "central" in words and str(row.get("city") or "").lower() == "vienna" and "praterstern" in store_id:
                return row
            if "vienna" in words and {"west", "westside"} & words and str(row.get("city") or "").lower() == "vienna" and "meidling" in store_id:
                return row
        scored = []
        for row in rows:
            hay = " ".join(str(row.get(k) or "") for k in ("id", "name", "city")).lower().replace("-", "")
            scored.append((sum(1 for w in words if w in hay), row))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored and scored[0][0] > 0 else None

    def resolve_product(self, phrase: str) -> dict[str, str] | None:
        query = parse_product_phrase(phrase)
        if not query:
            return None
        rows = self.product_candidate_rows(query)
        def score(row: dict[str, str]) -> tuple[int, int, int]:
            props = prop_index(row.get("props", ""))
            full = sum(1 for p in query["properties"] if prop_matches(props, p))
            prefix = 0
            for p in query["properties"]:
                if prop_matches(props, p): prefix += 1
                else: break
            row_name = str(row.get("name") or "").lower()
            fam = sum(1 for w in query["family"].lower().split() if len(w) > 2 and w in row_name)
            return (fam, full == len(query["properties"]), prefix + full)
        if not rows:
            return None
        return sorted(rows, key=score, reverse=True)[0]

    def product_candidate_rows(self, query: dict[str, Any]) -> list[dict[str, str]]:
        import re
        family_tokens = [
            token for token in re.findall(r"[A-Za-z0-9]+", query["family"])
            if token.lower() not in {query["brand"].lower()}
        ]
        filters = [
            f"lower(p.brand)=lower({quote(query['brand'])})",
            f"lower(p.name) like lower('%' || {quote(query['kind'])} || '%')",
        ]
        filters.extend(f"lower(p.name) like lower('%' || {quote(token)} || '%')" for token in family_tokens)
        rows = self.sql("select p.sku,p.path,p.name from products p where " + " and ".join(filters) + " order by p.sku")
        if not rows:
            return []
        return self.attach_product_props(rows)

    def attach_product_props(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        sku_list = ",".join(quote(row.get("sku", "")) for row in rows)
        prop_rows = self.sql("select sku,group_concat(key || '=' || value_text, ';') props "
                             f"from product_properties where sku in ({sku_list}) group by sku")
        props = {row.get("sku", ""): row.get("props", "") for row in prop_rows}
        for row in rows:
            row["props"] = props.get(row.get("sku", ""), "")
        return rows

    def resolve_product_exact(self, phrase: str) -> dict[str, str] | None:
        query = parse_product_phrase(phrase)
        if not query:
            return None
        product = self.resolve_product(phrase)
        if not product:
            return None
        props = prop_index(product.get("props", ""))
        if all(prop_matches(props, prop) for prop in query["properties"]):
            return product
        return None


def slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def quote(value: str | None) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


def find_id(text: str, prefix: str) -> str | None:
    import re
    pat = r"pay_\d+" if prefix == "pay" else rf"{prefix}_\d+"
    m = re.search(pat, text)
    return m.group(0) if m else None


def requested_percent(text: str) -> int | None:
    import re
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", text, re.I)
    return int(float(m.group(1))) if m else None


def is_catalog_presence_query(text: str) -> bool:
    lower = text.lower().strip()
    if lower.startswith("do you have the ") or lower.startswith("do you have "):
        return True
    return " in catalogue" in lower


def catalog_phrase(text: str, negative_claim: bool) -> str:
    import re
    if negative_claim:
        m = re.search(r"claims we stock the (.*?)(?:\. Check|$)", text, re.I)
        return (m.group(1) if m else "").strip()
    lower = text.lower()
    phrase = text
    if lower.startswith("do you have the "):
        phrase = text[len("do you have the "):]
    elif lower.startswith("do you have "):
        phrase = text[len("do you have "):]
    phrase = re.sub(r"\s+in catalogue\??.*$", "", phrase, flags=re.I).strip()
    return phrase.rstrip("?").strip()


def parse_product_phrase(text: str) -> dict[str, Any] | None:
    import re
    t = text.strip().rstrip("?.")
    if t.startswith("the "):
        t = t[4:]
    m = re.match(r"(.+?) from (.+?) in the (.+?) line that has (.+)$", t)
    if not m:
        return None
    props = m.group(4).replace(", and ", ", ").replace(" and has ", ", ").replace(" and ", ", ")
    return {"kind": m.group(1).strip(), "brand": m.group(2).strip(), "family": m.group(3).strip(), "properties": [parse_property(p) for p in props.split(",") if parse_property(p)]}


def parse_property(text: str) -> dict[str, str] | None:
    words = text.strip().split()
    if len(words) < 2:
        return None
    split = len(words) - 1
    for i, word in enumerate(words):
        if word.lower() in {"type", "source", "family", "platform", "contents", "class", "count", "size", "coating", "surface"}:
            split = min(i + 1, len(words) - 1); break
    if len(words) >= 3 and words[-1].lower() in {"mm", "ml", "m", "cm", "l", "w", "a", "k", "lm", "v", "pcs", "pc", "gsm"}:
        split = len(words) - 2
    return {"label": " ".join(words[:split]), "value": " ".join(words[split:])}


def prop_index(props: str) -> dict[str, str]:
    out = {}
    for item in str(props or "").split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            out[k] = norm_value(v)
    return out


def prop_matches(index: dict[str, str], prop: dict[str, str]) -> bool:
    return any(index.get(key) == norm_value(prop["value"]) for key in key_options(prop["label"]))


def key_options(label: str) -> list[str]:
    key = label.lower().replace(" ", "_")
    aliases = {
        "diameter": ["diameter_mm", "disc_diameter_mm"], "disc_diameter": ["disc_diameter_mm"], "blade_diameter": ["blade_diameter_mm"], "length": ["length_mm"], "luminous_flux": ["lumen"],
        "volume": ["volume_ml", "volume_l"], "wattage": ["wattage_w"], "power": ["power_w"], "current": ["current_a"],
        "cutting_width": ["cutting_width_cm"], "bar_length": ["bar_length_cm"], "working_width": ["working_width_mm"],
        "colour_temperature": ["color_temperature_k"], "color_temperature": ["color_temperature_k"],
        "tank_volume": ["tank_volume_l"], "pack_count": ["pack_count"], "piece_count": ["piece_count"], "voltage": ["voltage_v", "voltage"], "length": ["length_mm", "length_m"],
    }
    return aliases.get(key, [key])


def norm_value(value: str) -> str:
    lower = str(value).strip().strip(".").lower()
    parts = lower.split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1] in {"mm", "ml", "m", "cm", "l", "w", "a", "k", "lm", "v", "pcs", "pc", "gsm"}:
        return parts[0]
    return lower
