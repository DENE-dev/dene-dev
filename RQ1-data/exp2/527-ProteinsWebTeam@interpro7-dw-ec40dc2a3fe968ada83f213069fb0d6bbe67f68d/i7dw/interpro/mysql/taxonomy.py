import os
import json
from tempfile import mkstemp
from typing import Optional

from . import entry, structure, reduce
from .. import oracle
from ... import dbms, logger
from ...io import KVdb, Store


def insert_taxa(ora_uri, my_uri, chunk_size=100000):
    taxa = oracle.get_taxa(ora_uri)

    con, cur = dbms.connect(my_uri)

    data = [(
        taxon['id'],
        taxon['sci_name'],
        taxon['full_name'],
        # leading/trailing whitespaces are important from API queries
        ' {} '.format(' '.join(taxon['lineage'])),
        taxon['parent_id'],
        taxon['rank'],
        json.dumps(taxon['children'])
    ) for taxon in taxa]

    for i in range(0, len(data), chunk_size):
        cur.executemany(
            """
            INSERT INTO webfront_taxonomy (
                accession,
                scientific_name,
                full_name,
                lineage,
                parent_id,
                rank,
                children
            ) VALUES (
              %s, %s, %s, %s, %s, %s, %s
            )
            """,
            data[i:i+chunk_size]
        )

    cur.close()
    con.commit()
    con.close()


def get_taxa(uri: str, lineage: bool=False) -> dict:
    con, cur = dbms.connect(uri)
    if lineage:
        cur.execute(
            """
            SELECT accession, scientific_name, full_name, lineage, rank
            FROM webfront_taxonomy
            """
        )
        taxa = {}
        for row in cur:
            taxa[row[0]] = {
                "taxId": row[0],
                "scientificName": row[1],
                "fullName": row[2],
                "lineage": row[3].strip().split(),
                "rank": row[4]
            }
    else:
        cur.execute(
            """
            SELECT accession, scientific_name, full_name
            FROM webfront_taxonomy
            """
        )
        cols = ("taxId", "scientificName", "fullName")
        taxa = {row[0]: dict(zip(cols, row)) for row in cur}

    cur.close()
    con.close()

    return taxa


def iter_lineage(uri: str):
    con, cur = dbms.connect(uri)
    cur.execute("SELECT accession, lineage FROM webfront_taxonomy")
    for row in cur:
        yield row[0], row[1].strip().split()

    cur.close()
    con.close()


def export_xrefs(my_uri: str, src_proteins: str, src_proteomes:str,
                 src_matches: str, src_ida: str, processes: int=1,
                 sync_frequency: int=1000,
                 tmpdir: Optional[str]=None) -> Store:
    # Get required MySQL data
    entries = entry.get_entries(my_uri)
    entry2set = entry.get_entry2set(my_uri)
    protein2structures = structure.get_protein2structures(my_uri)
    lineage = dict(iter_lineage(my_uri))

    # Open existing stores containing protein-related info
    proteins = Store(src_proteins)
    protein2proteome = Store(src_proteomes)
    protein2matches = Store(src_matches)
    protein2ida = Store(src_ida)

    """
    Not using context manager so __exit__ is not called
    (which would delete tmp files)
    """
    xrefs = Store(keys=Store.chunk_keys(lineages, 10), tmpdir=tmpdir)

    protein_counts = {}
    cnt_proteins = 0
    for protein_acc, p in proteins:
        cnt_proteins += 1
        if not cnt_proteins % 10000000:
            logger.info(f"{cnt_proteins:>12}")

        protein_tax_id = p["taxon"]
        prot_entries = set()
        for match in protein2matches.get(protein_acc, []):
            method_acc = match["method_ac"]
            prot_entries.add(method_acc)

            entry_acc = entries[method_acc]["integrated"]
            if entry_acc:
                prot_entries.add(entry_acc)

        entry_databases = {}
        entry_sets = set()
        for entry_acc in prot_entries:
            database = entries[entry_acc]["database"]
            if database in entry_databases:
                entry_databases[database].add(entry_acc)
            else:
                entry_databases[database] = {entry_acc}

            if entry_acc in entry2set:
                entry_sets.add(entry2set[entry_acc])

        _xrefs = {
            "domain_architectures": set(),
            "entries": entry_databases,
            "proteomes": set(),
            "sets": entry_sets,
            "structures": set()
        }
        try:
            ida, ida_id = protein2ida[protein_acc]
        except KeyError:
            pass
        else:
            _xrefs["domain_architectures"].add(ida)

        try:
            upid = protein2proteome[protein_acc]
        except KeyError:
            pass
        else:
            _xrefs["proteomes"].add(upid)

        try:
            pdbe_ids = protein2structures[protein_acc]
        except KeyError:
            pass
        else:
            _xrefs["structures"] = pdbe_ids

        for tax_id in lineages[protein_tax_id]:
            if tax_id in protein_counts:
                protein_counts[tax_id] += 1
            else:
                protein_counts[tax_id] = 1

        xrefs.update(protein_tax_id, _xrefs)
        if not cnt_proteins % sync_frequency:
            xrefs.sync()

    proteins.close()
    protein2proteome.close()
    protein2matches.close()
    protein2ida.close()
    logger.info(f"{cnt_proteins:>12}")

    for tax_id in lineages:
        _xrefs = {
            "domain_architectures": set(),
            "entries": {},
            "proteomes": set(),
            "sets": set(),
            "structures": set()
        }
        try:
            cnt = protein_counts[tax_id]
        except KeyError:
            cnt = 0
        finally:
            _xrefs["proteins"] = cnt
            xrefs.update(tax_id, _xrefs)

    return xrefs


def update_counts(my_uri: str, src_proteins: str, src_proteomes:str,
                  src_matches: str, src_ida: str, processes: int=1,
                  sync_frequency: int=100000, tmpdir: Optional[str]=None):
    logger.info("starting")
    if tmpdir:
        os.makedirs(tmpdir, exist_ok=True)

    xrefs = export_xrefs(my_uri, src_proteins, src_proteomes, src_matches,
                        src_ida, processes, sync_frequency, tmpdir)
    size = xrefs.merge(processes=processes)

    logger.info("creating taxonomy database")
    fd, db_file = mkstemp(dir=tmpdir, suffix=".db")
    os.close(fd)
    os.remove(db_file)

    with KVdb(db_file, insertonly=True) as kvdb:
        for tax_id, _xrefs in xrefs:
            kvdb[tax_id] = _xrefs

    xrefs.close()  # delete temporary Store

    logger.info("propagating to lineage")
    with KVdb(db_file, writeback=True) as kvdb:
        cnt_taxa = 0
        keys = ("domain_architectures", "proteomes", "structures", "sets")
        for tax_id, lineage in iter_lineage(my_uri):
            node = kvdb[tax_id]
            for _tax_id in lineage:
                if _tax_id == tax_id:
                    continue

                _node = kvdb[_tax_id]
                for key in keys:
                    _node[key] |= node[key]

                for db, accessions in node["entries"].items():
                    try:
                        _node["entries"][db] |= accessions
                    except KeyError:
                        # Copy original set
                        _node["entries"][db] = set(accessions)

                kvdb[_tax_id] = _node

            cnt_taxa += 1
            if not cnt_taxa % sync_frequency:
                kvdb.sync()
                logger.info(f"{cnt_taxa:>8,}")

        size += kvdb.size
        logger.info("disk usage: {:.0f}MB".format(size/1024**2))

        con, cur = dbms.connect(my_uri)
        cur.close()
        query = "UPDATE webfront_taxonomy SET counts = %s WHERE accession = %s"
        with dbms.Populator(con, query) as table:
            for tax_id, _xrefs in kvdb:
                counts = reduce(_xrefs)
                counts["entries"]["total"] = sum(counts["entries"].values())
                table.update((json.dumps(counts), tax_id))

        con.commit()
        con.close()

    os.remove(db_file)
    logger.info("complete")