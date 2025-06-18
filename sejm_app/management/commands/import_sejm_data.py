import requests
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import json # Pamiętaj o imporcie!

# Upewnij się, że masz poprawne importy modeli
from sejm_app.models import Member, Voting, Vote

class Command(BaseCommand):
    help = 'Imports data about Members of Parliament and Votings from Sejm API.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--term',
            type=int,
            default=10, # Domyślna kadencja (np. 10 dla obecnej)
            help='Specify the parliamentary term (kadencja) to import data from.',
        )
        parser.add_argument(
            '--import-members',
            action='store_true',
            help='Import only members data.',
        )
        parser.add_argument(
            '--import-votings',
            action='store_true',
            help='Import only votings data.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not save data to the database, just show what would be imported.',
        )
        parser.add_argument(
            '--skip-member-deactivation',
            action='store_true',
            help='Skip deactivating all existing members before import (use with caution).',
        )


    def handle(self, *args, **options):
        term = options['term']
        import_members_only = options['import_members']
        import_votings_only = options['import_votings']
        dry_run = options['dry_run']
        skip_member_deactivation = options['skip_member_deactivation']

        # Domyślnie importuj wszystko, chyba że wybrano konkretne opcje
        if not import_members_only and not import_votings_only:
            import_members_only = True
            import_votings_only = True

        API_BASE_URL = os.getenv('PARLIAMENT_API_BASE_URL', 'https://api.sejm.gov.pl')

        self.stdout.write(self.style.SUCCESS(f'Starting data import for Sejm Term {term} from {API_BASE_URL}...'))

        if import_members_only:
            self._import_members(API_BASE_URL, term, dry_run, skip_member_deactivation)
        if import_votings_only:
            self._import_votings(API_BASE_URL, term, dry_run)

        self.stdout.write(self.style.SUCCESS('Data import finished.'))

    def _get_api_data(self, url):
        """Pomocnicza funkcja do pobierania danych z API."""
        self.stdout.write(f"Fetching data from: {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status() # Wyrzuci wyjątek dla kodów błędów HTTP (4xx lub 5xx)
            return response.json()
        except requests.exceptions.Timeout:
            self.stderr.write(self.style.ERROR(f"Timeout occurred while fetching data from {url}"))
            return None
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Error fetching data from {url}: {e}"))
            return None

    def _import_members(self, base_url, term, dry_run, skip_member_deactivation):
        self.stdout.write(f'\nImporting Members for Term {term}...')
        members_url = f'{base_url}/sejm/term{term}/MP'
        members_data = self._get_api_data(members_url)

        if not members_data:
            self.stderr.write(self.style.ERROR('No member data received.'))
            return

        if dry_run:
            self.stdout.write(self.style.NOTICE(f'Dry run: Would import {len(members_data)} members.'))
            for i, member_info in enumerate(members_data[:5]): # Wyświetl pierwsze 5 dla podglądu
                self.stdout.write(f'  {i+1}. API ID: {member_info.get("id")} - {member_info.get("firstName")} {member_info.get("lastName")}')
                # print(json.dumps(member_info, indent=2)) # Odkomentuj dla pełnego podglądu JSON
            return

        with transaction.atomic():
            if not skip_member_deactivation:
                # Dezaktywuj wszystkich obecnych posłów przed importem, aby oznaczyć nieaktywnych
                Member.objects.all().update(active=False)
                self.stdout.write(self.style.WARNING('Deactivated all existing members for update.'))
            else:
                self.stdout.write(self.style.NOTICE('Skipping deactivation of existing members.'))


            for i, member_info in enumerate(members_data):
                # Zgodnie z Twoim JSON-em posłów:
                sejm_id = member_info.get('id')
                first_name = member_info.get('firstName') # Poprawione na 'firstName'
                last_name = member_info.get('lastName')   # Poprawione na 'lastName'
                club = member_info.get('club')
                district_name = member_info.get('districtName')
                district_num = member_info.get('districtNum')
                voivodeship = member_info.get('voivodeship')
                email = member_info.get('email')
                active = member_info.get('active', True)

                if not sejm_id:
                    self.stderr.write(self.style.WARNING(f"Skipping member without 'id': {first_name} {last_name}"))
                    continue

                member, created = Member.objects.update_or_create(
                    sejm_id=sejm_id,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'club': club,
                        'district_name': district_name,
                        'district_num': district_num,
                        'voivodeship': voivodeship,
                        'email': email,
                        'active': active,
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created member: {first_name} {last_name} (ID: {sejm_id})'))
                else:
                    self.stdout.write(self.style.NOTICE(f'Updated member: {first_name} {last_name} (ID: {sejm_id})'))

                if (i + 1) % 50 == 0:
                    self.stdout.write(f"Processed {i + 1} members...")

        self.stdout.write(self.style.SUCCESS(f'Successfully processed {len(members_data)} members.'))

    def _import_votings(self, base_url, term, dry_run):
        self.stdout.write(f'\nImporting Votings for Term {term}...')
        # Krok 1: Pobierz ogólną listę głosowań
        all_votings_summary_url = f'{base_url}/sejm/term{term}/votings'
        votings_summary_data = self._get_api_data(all_votings_summary_url)

        if not votings_summary_data:
            self.stderr.write(self.style.ERROR('No voting summary data received.'))
            return

        if dry_run:
            self.stdout.write(self.style.NOTICE(f'Dry run: Would process {len(votings_summary_data)} votings.'))
            self.stdout.write(self.style.NOTICE('First 5 votings summary data:'))
            for i, voting_sum in enumerate(votings_summary_data[:5]):
                self.stdout.write(f"  {voting_sum.get('sittingDay')}/{voting_sum.get('votingNumber')} - {voting_sum.get('title')}")
                # print(json.dumps(voting_sum, indent=2)) # Odkomentuj dla pełnego podglądu JSON summary
            return

        with transaction.atomic():
            imported_votings_count = 0
            imported_votes_count = 0
            total_votings_to_process = len(votings_summary_data)
            self.stdout.write(f"Found {total_votings_to_process} votings to process for detailed import.")

            for i, voting_summary_info in enumerate(votings_summary_data):
                sitting_day = voting_summary_info.get('sittingDay')
                voting_number = voting_summary_info.get('votingNumber')
                # Używamy title_summary tylko do logowania, właściwy title będzie z detailed_voting_data
                title_summary = voting_summary_info.get('title')

                if not sitting_day or not voting_number:
                    self.stderr.write(self.style.WARNING(f"Skipping voting summary due to missing sittingDay or votingNumber: {title_summary}"))
                    continue

                # Krok 2: Pobierz szczegółowe dane dla każdego głosowania
                detail_voting_url = f'{base_url}/sejm/term{term}/votings/{sitting_day}/{voting_number}'
                detailed_voting_data = self._get_api_data(detail_voting_url)

                if not detailed_voting_data:
                    self.stderr.write(self.style.ERROR(f"Could not fetch detailed data for voting {sitting_day}/{voting_number}. Skipping."))
                    continue

                # Wyciąganie danych ze szczegółowego JSON-a (Zgodnie z Twoim JSON-em głosowania)
                date_str = detailed_voting_data.get('date')
                title = detailed_voting_data.get('title')
                topic = detailed_voting_data.get('topic')
                kind = detailed_voting_data.get('kind')
                majority_type = detailed_voting_data.get('majorityType')
                majority_votes = detailed_voting_data.get('majorityVotes')
                yes = detailed_voting_data.get('yes')
                no = detailed_voting_data.get('no')
                abstain = detailed_voting_data.get('abstain')
                not_participating = detailed_voting_data.get('notParticipating')
                present = detailed_voting_data.get('present')
                total_voted = detailed_voting_data.get('totalVoted')
                links = detailed_voting_data.get('links')
                sitting = detailed_voting_data.get('sitting')
                votes_list = detailed_voting_data.get('votes', []) # Lista indywidualnych głosów posłów

                # Konwersja daty (format "YYYY-MM-DDTHH:MM:SS")
                date_obj = None
                if date_str:
                    try:
                        date_obj = timezone.datetime.fromisoformat(date_str)
                    except ValueError as e:
                        self.stderr.write(self.style.ERROR(f"Could not parse date '{date_str}' for voting {voting_number} ({title}): {e}"))
                        continue # Pomiń głosowanie jeśli data jest błędna

                # Utwórz lub zaktualizuj obiekt Voting
                voting, created = Voting.objects.update_or_create(
                    voting_number=voting_number,
                    sitting_day=sitting_day,
                    term=term, # Zapewnij, że to pole jest brane pod uwagę w unique_together i defaults
                    defaults={
                        'date': date_obj,
                        'title': title,
                        'topic': topic,
                        'kind': kind,
                        'majority_type': majority_type,
                        'majority_votes': majority_votes,
                        'yes': yes,
                        'no': no,
                        'abstain': abstain,
                        'not_participating': not_participating,
                        'present': present,
                        'total_voted': total_voted,
                        'links': links,
                        'sitting': sitting,
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created voting: {voting_number}/{sitting_day} - {title}'))
                else:
                    self.stdout.write(self.style.NOTICE(f'Updated voting: {voting_number}/{sitting_day} - {title}'))

                # Przetwórz indywidualne głosy
                if votes_list:
                    # Usuń stare głosy dla tego głosowania, jeśli aktualizujesz
                    # To zapobiega duplikatom przy ponownym uruchomieniu
                    if not created: # Tylko jeśli głosowanie już istniało i jest aktualizowane
                        voting.individual_votes.all().delete()
                        # self.stdout.write(self.style.NOTICE(f'Cleared old votes for voting {voting.id}'))


                    for vote_info in votes_list:
                        mp_id_api = vote_info.get('MP')
                        first_name = vote_info.get('firstName') # 'firstName' z API
                        last_name = vote_info.get('lastName')   # 'lastName' z API
                        club = vote_info.get('club')
                        vote_choice = vote_info.get('vote') # np. 'YES', 'NO', 'ABSTAIN'

                        if not mp_id_api or not vote_choice:
                            self.stderr.write(self.style.WARNING(f"Skipping individual vote for voting {voting.id} due to missing MP ID or vote choice."))
                            continue

                        member_obj = None
                        try:
                            member_obj = Member.objects.get(sejm_id=mp_id_api)
                        except Member.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f"Member with sejm_id {mp_id_api} ({first_name} {last_name}) not found. Storing vote without linked Member object."))

                        # Utwórz obiekt Vote
                        # Używamy update_or_create z (voting, member, mp_id_api) aby zapobiec duplikatom
                        Vote.objects.update_or_create(
                            voting=voting,
                            member=member_obj,
                            mp_id_api=mp_id_api, # Zawsze zapisuj ID z API, nawet jeśli member_obj is None
                            defaults={
                                'first_name': first_name,
                                'last_name': last_name,
                                'club': club,
                                'vote_choice': vote_choice,
                            }
                        )
                        imported_votes_count += 1
                imported_votings_count += 1
                if imported_votings_count % 10 == 0:
                    self.stdout.write(f"Processed {imported_votings_count}/{total_votings_to_process} votings. Total individual votes: {imported_votes_count}")

        self.stdout.write(self.style.SUCCESS(f'Successfully processed {imported_votings_count} votings and {imported_votes_count} individual votes.'))