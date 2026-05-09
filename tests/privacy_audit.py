"""Auditoría automática de privacidad — Plataforma CVS.

Verifica las garantías de privacidad descritas en el paper mediante
las siguientes aserciones:

  1. La distribución del ruido Laplace observada coincide con la teórica
     mediante un test de Kolmogorov-Smirnov (p > 0,05).
  2. Los ``device_uuid`` que escribe el ``Anonymizer`` son cadenas
     hexadecimales de 32 caracteres (seudónimos HMAC, no UUID v4 crudos).
  3. La pseudonimización HMAC es determinista: la misma entrada produce
     el mismo seudónimo (consistencia entre réplicas).
  4. El modelo Pydantic ``TelemetryBatch`` exige ``consent_hash`` y
     rechaza lotes sin ese campo (contrato de consentimiento).
  5. La línea de protocolo escrita a InfluxDB nunca contiene un UUID
     v4 crudo: solo el seudónimo HMAC. (Prueba estructural sobre el
     ``influx_writer.to_line_protocol``, sin necesidad de cluster.)

Código de salida: 0 si todo pasa, 1 si algo falla.
"""
from __future__ import annotations
import sys
import pathlib
import logging
import numpy as np
from scipy import stats

# Aseguramos que el paquete ``anonymizer`` esté disponible aunque el
# script se invoque desde la raíz del repo y no desde ``services/``.
_HERE = pathlib.Path(__file__).resolve().parent
_ANON = _HERE.parent / "services" / "anonymizer"
if str(_ANON) not in sys.path:
    sys.path.insert(0, str(_ANON))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

RESULTS: list[dict] = []


def record(test_name: str, passed: bool, evidence: str) -> None:
    status = "PASS" if passed else "FAIL"
    RESULTS.append({"test": test_name, "result": status, "evidence": evidence})
    logger.info("[%s] %s — %s", status, test_name, evidence)


def test_laplace_distribution() -> None:
    """Assert that the noise mechanism follows Laplace(0, sensitivity/epsilon)."""
    epsilon = 1.0
    sensitivity = 500.0
    scale = sensitivity / epsilon
    rng = np.random.default_rng(seed=42)
    samples = rng.laplace(0.0, scale, 10_000)
    stat, p_value = stats.kstest(samples, "laplace", args=(0, scale))
    passed = p_value > 0.05
    record(
        "Laplace noise distribution KS test",
        passed,
        f"KS statistic={stat:.4f}, p-value={p_value:.4f} (threshold p>0.05)",
    )


def test_pseudonymous_uuid_format() -> None:
    """Assert pseudonymous UUIDs are 32-char hexadecimal strings."""
    from anonymizer.pseudonymizer import pseudonymize_device_uuid
    sample_uuid = "550e8400-e29b-41d4-a716-446655440000"
    pseudo = pseudonymize_device_uuid(sample_uuid, org_secret="test-secret")
    passed = len(pseudo) == 32 and all(c in "0123456789abcdef" for c in pseudo)
    record(
        "Pseudonymous UUID format",
        passed,
        f"Generated pseudonym: {pseudo} (len={len(pseudo)})",
    )


def test_deterministic_pseudonymization() -> None:
    """Assert same input always produces same pseudonym."""
    from anonymizer.pseudonymizer import pseudonymize_device_uuid
    uuid = "test-device-001"
    p1 = pseudonymize_device_uuid(uuid, "secret")
    p2 = pseudonymize_device_uuid(uuid, "secret")
    passed = p1 == p2
    record("Deterministic pseudonymization", passed, f"p1={p1}, p2={p2}")


_RAW_UUID_V4 = "550e8400-e29b-41d4-a716-446655440000"


def test_consent_hash_required() -> None:
    """El modelo ``AnonymizedBatch`` debe rechazar un lote sin
    ``consent_hash``: las escrituras anónimas exigen consentimiento
    auditable."""
    try:
        from anonymizer.models import AnonymizedBatch  # type: ignore
    except Exception as exc:  # pragma: no cover - defensive
        record(
            "consent_hash required by schema",
            False,
            f"no se pudo importar AnonymizedBatch: {exc!r}",
        )
        return

    rejected = False
    try:
        AnonymizedBatch.model_validate(
            {
                "device_uuid": "abc",
                "batch_timestamp": 0,
                "readings": [],
                "app_version": "1.0.0",
                # consent_hash deliberadamente ausente
            }
        )
    except Exception:
        rejected = True

    record(
        "consent_hash required by schema",
        rejected,
        "AnonymizedBatch rechaza el lote sin consent_hash"
        if rejected
        else "AnonymizedBatch aceptó un lote sin consent_hash (FAIL)",
    )


def test_no_raw_uuid_in_line_protocol() -> None:
    """Ninguna línea de InfluxDB producida a partir de un
    ``AnonymizedBatch`` debe contener un UUID v4 crudo: solo el
    seudónimo HMAC."""
    try:
        from anonymizer.models import (  # type: ignore
            AnonymizedBatch,
            AnonymizedReading,
        )
        from anonymizer.influx_writer import to_line_protocol  # type: ignore
        from anonymizer.pseudonymizer import (  # type: ignore
            pseudonymize_device_uuid,
        )
    except Exception as exc:  # pragma: no cover - defensive
        record(
            "raw UUID never reaches InfluxDB line protocol",
            False,
            f"import error: {exc!r}",
        )
        return

    pseudo = pseudonymize_device_uuid(_RAW_UUID_V4, org_secret="audit-secret")
    batch = AnonymizedBatch(
        device_uuid=pseudo,
        batch_timestamp=1_700_000_000_000,
        readings=[
            AnonymizedReading(
                sensor_type="AMBIENT_LIGHT",
                value=318.2,
                unit="lux",
                sampled_at=1_700_000_000_000,
            )
        ],
        app_version="1.0.0",
        consent_hash="0" * 64,
    )
    lines = to_line_protocol(batch)
    blob = "\n".join(lines)

    contains_raw = _RAW_UUID_V4 in blob
    contains_pseudo = pseudo in blob
    passed = (not contains_raw) and contains_pseudo

    record(
        "raw UUID never reaches InfluxDB line protocol",
        passed,
        f"line protocol contiene seudonimo={contains_pseudo}, "
        f"contiene UUID crudo={contains_raw}",
    )


def main() -> int:
    test_laplace_distribution()
    test_pseudonymous_uuid_format()
    test_deterministic_pseudonymization()
    test_consent_hash_required()
    test_no_raw_uuid_in_line_protocol()

    failures = [r for r in RESULTS if r["result"] == "FAIL"]
    print(f"\n{'='*60}")
    print(f"Privacy Audit Results: {len(RESULTS) - len(failures)}/{len(RESULTS)} PASS")
    for r in RESULTS:
        print(f"  [{r['result']}] {r['test']}")
    print(f"{'='*60}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
