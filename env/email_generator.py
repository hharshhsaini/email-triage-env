"""
Synthetic email generator for the Email Triage Agent Environment.

All generation is seeded and fully deterministic - given the same seed
and parameters, the output inbox is always identical. This guarantees
reproducible training and evaluation splits.
"""

import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from env.models import Email, EmailWithContext


# ---------------------------------------------------------------------------
# Type-to-distribution mapping (realistic enterprise inbox ratios)
# ---------------------------------------------------------------------------
DEFAULT_TYPE_WEIGHTS: Dict[str, float] = {
    "urgent":         0.05,
    "meeting":        0.15,
    "internal":       0.20,
    "hr":             0.10,
    "billing":        0.08,
    "customer":       0.12,
    "newsletter":     0.20,
    "spam":           0.10,
    "action_required": 0.10,
    "fyi":            0.05,
}

# Probability that any given email is actually a reply in a thread
REPLY_PROBABILITY = 0.15

# Ground-truth priority mapping by email type (used for reward grading)
TYPE_TO_PRIORITY = {
    "urgent":          "urgent",
    "action_required": "high",
    "billing":         "normal",
    "customer":        "normal",
    "meeting":         "normal",
    "internal":        "normal",
    "hr":              "normal",
    "fyi":             "low",
    "newsletter":      "low",
    "spam":            "spam",
}

# Ground-truth category mapping by email type
TYPE_TO_CATEGORY = {
    "urgent":          "action_required",
    "action_required": "action_required",
    "billing":         "billing",
    "customer":        "customer",
    "meeting":         "meeting",
    "internal":        "internal",
    "hr":              "hr",
    "fyi":             "fyi",
    "newsletter":      "newsletter",
    "spam":            "spam",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_templates(templates_path: Optional[str] = None) -> Dict[str, List[Dict]]:
    """Load email templates from the bundled JSON file."""
    if templates_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        templates_path = os.path.join(here, "..", "data", "email_templates.json")
    with open(os.path.normpath(templates_path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _pick(rng: random.Random, seq: list) -> Any:
    """Pick a random element from a non-empty sequence."""
    return rng.choice(seq)


def _slug(text: str) -> str:
    """Create a lowercase slug from text (first 3 words, alphanumeric)."""
    words = text.lower().split()[:3]
    return "_".join("".join(c for c in w if c.isalnum()) for w in words)


# ---------------------------------------------------------------------------
# Realistic name / sender pools used when templates need variation
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Alice", "Bob", "Carol", "David", "Emily", "Frank", "Grace", "Henry",
    "Isabella", "James", "Karen", "Lucas", "Maria", "Nathan", "Olivia",
    "Patrick", "Rachel", "Samuel", "Tina", "Umar", "Victoria", "William",
    "Xuan", "Yara", "Zach",
]
LAST_NAMES = [
    "Smith", "Johnson", "Chen", "Patel", "Kim", "Garcia", "Martinez",
    "Lee", "Williams", "Brown", "Taylor", "Anderson", "Thomas", "Jackson",
    "White", "Harris", "Martin", "Thompson", "Wilson", "Moore",
]
COMPANY_NAMES = [
    "GlobalTech", "Acme Corp", "ClientCorp", "Nexus Systems", "Apex Ltd",
    "Stellar Inc", "Zenith Partners", "Horizon Group", "Summit Analytics",
    "Pinnacle Solutions",
]
EXTERNAL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "clientcorp.com", "bigclient.com", "techcorp.io", "external.com",
]

# Invoice / order number patterns
def _inv_number(rng: random.Random) -> str:
    year = rng.choice([2024, 2025])
    return f"INV-{year}-{rng.randint(1000, 9999)}"

def _order_number(rng: random.Random) -> int:
    return rng.randint(10000, 99999)

def _ticket_number(rng: random.Random) -> int:
    return rng.randint(10000, 99999)


# ---------------------------------------------------------------------------
# Core generator class
# ---------------------------------------------------------------------------

class EmailGenerator:
    """
    Generates realistic synthetic enterprise emails.

    All generation is seeded and reproducible.

    Email types generated with realistic ratios:
    - Urgent client escalations          (5%)
    - Meeting requests / calendar invites (15%)
    - Internal project updates           (20%)
    - HR / admin notices                 (10%)
    - Billing / invoice notifications    (8%)
    - Customer support tickets           (12%)
    - Newsletter / marketing             (20%)
    - Spam                               (10%)
    - Action-required (boss/exec) emails (10%)
    - FYI forwards                       (5%)
    - Thread replies                     (15% of the above, creates reply chains)

    Parameters
    ----------
    seed : int
        Random seed for deterministic generation. Same seed always
        produces an identical inbox.
    templates_path : str, optional
        Override the path to email_templates.json.
    """

    def __init__(self, seed: int = 42, templates_path: Optional[str] = None):
        self.seed = seed
        self._rng = random.Random(seed)
        self._templates = _load_templates(templates_path)
        # Pre-build thread-id pool so reply chains are internally consistent
        self._thread_ids: List[str] = [str(uuid.UUID(int=self._rng.getrandbits(128))) for _ in range(500)]
        self._thread_cursor = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_inbox(
        self,
        n_emails: int,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[EmailWithContext], Dict[str, Any]]:
        """
        Generate a realistic inbox.

        Parameters
        ----------
        n_emails : int
            Number of emails to generate.
        task_config : dict, optional
            Configuration overrides:
            - ``email_types`` : dict mapping type name → relative weight
            - ``include_vip_senders`` : list of VIP email addresses
            - ``urgency_level`` : float in [0, 1]; boosts urgent/action_required
            - ``domain`` : company domain for internal sender addresses

        Returns
        -------
        inbox : List[EmailWithContext]
            Ordered list of emails (index 0 = newest).
        ground_truth : dict
            Mapping of email_id → {"priority": str, "category": str}.
        """
        if task_config is None:
            task_config = {}

        vip_senders: List[str] = task_config.get("include_vip_senders", [])
        urgency_level: float = float(task_config.get("urgency_level", 0.5))
        company_domain: str = task_config.get("domain", "company.com")

        # Build type weights
        weights = dict(DEFAULT_TYPE_WEIGHTS)
        if "email_types" in task_config:
            weights.update(task_config["email_types"])
        # Urgency level biases toward urgent / action_required
        if urgency_level != 0.5:
            delta = (urgency_level - 0.5) * 0.2
            weights["urgent"] = max(0.01, weights["urgent"] + delta)
            weights["action_required"] = max(0.01, weights["action_required"] + delta)
        # Normalise
        total_w = sum(weights.values())
        types = list(weights.keys())
        probs = [weights[t] / total_w for t in types]

        # Determine email type sequence deterministically
        email_types_seq = self._rng.choices(types, weights=probs, k=n_emails)

        # Track threads: thread_id → list of email_ids already in that thread
        active_threads: Dict[str, List[str]] = {}
        sender_history: Dict[str, int] = {}

        raw_emails: List[Email] = []
        ground_truth: Dict[str, Any] = {}

        base_time = datetime(2024, 10, 28, 9, 0, 0, tzinfo=timezone.utc)

        for i, etype in enumerate(email_types_seq):
            # Each email is offset backwards in time (newest first at idx 0
            # but we build chronologically and reverse at the end)
            offset_hours = i * self._rng.uniform(0.5, 4.0)
            timestamp = base_time - timedelta(hours=offset_hours)

            # Decide if this email is a reply in an existing thread
            is_reply = (
                len(active_threads) > 0
                and self._rng.random() < REPLY_PROBABILITY
            )

            email = self._generate_email(
                email_type=etype,
                position=i,
                timestamp=timestamp,
                company_domain=company_domain,
                vip_senders=vip_senders,
                is_reply=is_reply,
                active_threads=active_threads,
            )
            raw_emails.append(email)

            # Update sender history counts
            sender_history[email.sender] = sender_history.get(email.sender, 0) + 1

            # Maintain thread tracking
            if email.thread_id:
                thread_emails = active_threads.setdefault(email.thread_id, [])
                thread_emails.append(email.id)

            # Store ground truth (use template override if available)
            tpl = self._pick_template(etype)
            gt = tpl.get("ground_truth", {})
            ground_truth[email.id] = {
                "priority": gt.get("priority", TYPE_TO_PRIORITY.get(etype, "normal")),
                "category": gt.get("category", TYPE_TO_CATEGORY.get(etype, "internal")),
                "email_type": etype,
            }

        # Sort newest-first
        raw_emails.sort(key=lambda e: e.timestamp, reverse=True)

        # Compute thread lengths
        thread_lengths: Dict[str, int] = {}
        for e in raw_emails:
            if e.thread_id:
                thread_lengths[e.thread_id] = thread_lengths.get(e.thread_id, 0) + 1

        # Build EmailWithContext
        vip_set = set(vip_senders)
        inbox: List[EmailWithContext] = []
        for pos, email in enumerate(raw_emails):
            inbox.append(
                EmailWithContext(
                    **email.model_dump(),
                    inbox_position=pos,
                    thread_length=thread_lengths.get(email.thread_id or "", 1),
                    sender_history=sender_history.get(email.sender, 0) - 1,  # prior emails
                    is_vip_sender=email.sender in vip_set,
                )
            )

        return inbox, ground_truth

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _next_thread_id(self) -> str:
        tid = self._thread_ids[self._thread_cursor % len(self._thread_ids)]
        self._thread_cursor += 1
        return tid

    def _pick_template(self, email_type: str) -> Dict[str, Any]:
        """Pick a random template for the given type."""
        candidates = self._templates.get(email_type, [])
        if not candidates:
            candidates = [{"subject": f"[{email_type}] Notice", "body": "Please see the attached notice.", "sender_name": "System", "sender_email": f"system@company.com", "sender_domain": "company.com"}]
        return _pick(self._rng, candidates)

    def _make_sender(self, tpl: Dict[str, Any], company_domain: str) -> Tuple[str, str]:
        """Return (sender_email, sender_domain) from a template."""
        sender_email: str = tpl.get("sender_email", "")
        if not sender_email:
            first = _pick(self._rng, FIRST_NAMES).lower()
            last = _pick(self._rng, LAST_NAMES).lower()
            domain = tpl.get("sender_domain", company_domain)
            sender_email = f"{first}.{last}@{domain}"
        sender_domain = sender_email.split("@")[-1]
        return sender_email, sender_domain

    def _interpolate_subject(self, subject: str) -> str:
        """Replace template placeholders with random realistic values."""
        rng = self._rng
        replacements = {
            "{client}": _pick(rng, COMPANY_NAMES),
            "{inv}": _inv_number(rng),
            "{order}": str(_order_number(rng)),
            "{ticket}": str(_ticket_number(rng)),
            "{amount}": f"${rng.randint(500, 50000):,}.{rng.randint(0,99):02d}",
        }
        for key, val in replacements.items():
            subject = subject.replace(key, val)
        return subject

    def _generate_email(
        self,
        email_type: str,
        position: int,
        timestamp: datetime,
        company_domain: str,
        vip_senders: List[str],
        is_reply: bool,
        active_threads: Dict[str, List[str]],
    ) -> Email:
        """
        Generate one email of the given type.

        Parameters
        ----------
        email_type : str
            One of the keys in DEFAULT_TYPE_WEIGHTS.
        position : int
            Sequential index (for ID generation reproducibility).
        timestamp : datetime
            Timestamp to assign.
        company_domain : str
            Internal company email domain.
        vip_senders : list of str
            If non-empty, some emails will have VIP senders injected.
        is_reply : bool
            Whether to generate this as a reply in an existing thread.
        active_threads : dict
            Mutable mapping of thread_id → list of email IDs in that thread.

        Returns
        -------
        Email
        """
        rng = self._rng
        tpl = self._pick_template(email_type)

        sender_email, sender_domain = self._make_sender(tpl, company_domain)

        # With small probability inject a VIP sender
        if vip_senders and rng.random() < 0.15:
            sender_email = _pick(rng, vip_senders)
            sender_domain = sender_email.split("@")[-1]

        subject = self._interpolate_subject(tpl["subject"])
        body = tpl["body"]

        # Handle reply chains
        thread_id: Optional[str] = None
        original_email_id: Optional[str] = None

        if is_reply and active_threads:
            # Pick an existing thread to reply to
            thread_id = _pick(rng, list(active_threads.keys()))
            thread_emails = active_threads[thread_id]
            original_email_id = thread_emails[-1]  # Reply to latest in thread
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
        elif rng.random() < 0.4:
            # Start a new thread for this email
            thread_id = self._next_thread_id()

        # Attachments
        has_attachments: bool = tpl.get("has_attachments", False)
        attachment_names: List[str] = list(tpl.get("attachment_names", []))

        # CC list (occasional)
        cc: List[str] = []
        if rng.random() < 0.2:
            n_cc = rng.randint(1, 3)
            for _ in range(n_cc):
                fn = _pick(rng, FIRST_NAMES).lower()
                ln = _pick(rng, LAST_NAMES).lower()
                cc.append(f"{fn}.{ln}@{company_domain}")

        recipient = f"user@{company_domain}"

        email_id = f"email_{position:04d}_{_slug(subject)}"

        return Email(
            id=email_id,
            subject=subject,
            sender=sender_email,
            sender_domain=sender_domain,
            recipient=recipient,
            body=body,
            timestamp=timestamp,
            thread_id=thread_id,
            has_attachments=has_attachments,
            attachment_names=attachment_names,
            cc=cc,
            is_reply=is_reply,
            original_email_id=original_email_id,
            metadata={
                "email_type": email_type,
                "generation_seed": self.seed,
                "position": position,
            },
        )
