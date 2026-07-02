from django.core.management.base import BaseCommand
from claims.models import Claim
from ai_agents.claim_analyzer import analyze_claim


class Command(BaseCommand):
    help = 'Reanalyze claims with 0 confidence and update their AI scores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reanalyze ALL claims, not just those with 0 confidence',
        )
        parser.add_argument(
            '--employee-id',
            type=int,
            help='Reanalyze claims for a specific employee',
        )

    def handle(self, *args, **options):
        # Build query
        if options['all']:
            claims = Claim.objects.all()
            self.stdout.write("Reanalyzing ALL claims...")
        elif options['employee_id']:
            claims = Claim.objects.filter(employee_id=options['employee_id'])
            self.stdout.write(f"Reanalyzing claims for employee {options['employee_id']}...")
        else:
            claims = Claim.objects.filter(ai_confidence=0)
            self.stdout.write("Reanalyzing claims with ai_confidence = 0...")

        total = claims.count()
        updated = 0

        for claim in claims:
            try:
                # Skip policy-blocked claims
                if "POLICY BLOCKED" in (claim.ai_recommendation or ""):
                    self.stdout.write(
                        self.style.WARNING(
                            f"SKIP Claim {claim.id}: Policy blocked"
                        )
                    )
                    continue

                # Reanalyze
                ai_result = analyze_claim(
                    claim.title,
                    claim.amount,
                    claim.employee.id
                )

                # Update
                claim.ai_confidence = ai_result.get("confidence", 0)
                claim.fraud_score = ai_result.get("fraud_score", 0)
                claim.ai_recommendation = ai_result.get("ai_response", "")
                claim.ai_reasoning = ai_result.get("reasoning", "")
                claim.save()

                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Claim {claim.id}: confidence={claim.ai_confidence}, "
                        f"fraud_score={claim.fraud_score}"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Claim {claim.id}: {str(e)}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Updated {updated}/{total} claims successfully"
            )
        )
