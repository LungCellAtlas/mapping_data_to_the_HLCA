import scanpy as sc
import pandas as pd
import os
import numpy as np
import anndata

def import_testdata(testfolder):
    # read in adata
    query_data_full = sc.read_10x_h5(os.path.join(testfolder,"testfile.h5"))
    # clean up .var.index (gene names)
    query_data_full.var['gene_names'] = query_data_full.var.index
    query_data_full.var.index = [idx.split("___")[-1] for idx in query_data_full.var.gene_ids]
    # clean up cell barcodes:
    query_data_full.obs.index = query_data_full.obs.index.str.rstrip("-1")
    # read in metadata (to select only cells of interest and remove empty drops)
    query_data_meta = pd.read_csv(os.path.join(testfolder,"testmeta.csv.gz"),index_col=0)
    # subset to cells from our sample
    query_data_meta = query_data_meta.loc[query_data_meta.donor == "D12_4",:].copy()
    # clean up barcodes:
    query_data_meta.index = [idx.split("-")[-1] for idx in query_data_meta.index]
    # subset adata to cells in metadata:
    query_data_full = query_data_full[query_data_meta.index,:].copy()
    # add dataset information:
    query_data_full.obs['dataset'] = "test_dataset_delorey_regev"
    return query_data_full



def subset_and_pad_adata_object(adata, ref_genes_df, min_n_genes_included=1500):
    # test if adata.var.index has gene names or ensembl names:
    n_ids_detected = sum(adata.var.index.isin(ref_genes_df.gene_id))
    n_symbols_detected = sum(adata.var.index.isin(ref_genes_df.gene_symbol))
    if max(n_ids_detected, n_symbols_detected) < min_n_genes_included:
        # change column names to lower case
        adata.var.columns = adata.var.columns.str.lower()
        # check if gene names are in another column:
        if "gene_symbols" in adata.var.columns:
            adata.var.index = adata.var.gene_symbol
            n_symbols_detected = sum(adata.var.index.isin(ref_genes_df.gene_symbol))
        elif "gene_ids" in adata.var.columns:
            adata.var.index = adata.var.gene_ids
            n_ids_detected = sum(adata.var.index.isin(ref_genes_df.gene_id))
        # check if anything changed:
        if max(n_ids_detected, n_symbols_detected) < min_n_genes_included:    
            raise ValueError(f"We could detect only {max(n_ids_detected, n_symbols_detected)} genes of the 2000 that we need for the mapping! The minimum overlap is {min_n_genes_included}. Contact the HLCA team for questions. Exiting")
    else:
        if n_ids_detected >= n_symbols_detected:
            gene_type = "gene_id"
            print("Gene names detected: ensembl gene ids.")
            n_genes = n_ids_detected  
        else:
            gene_type = "gene_symbol"
            n_genes = n_symbols_detected
            print("Gene names detected: ensembl gene symbols.")
    genes = adata.var.index[adata.var.index.isin(ref_genes_df[gene_type])].tolist()
    # if not all genes are included, pad:
    if n_genes > 2000:
        raise ValueError("Your gene names appear not to be unique, something must be wrong. Exiting.")
    print(f"{n_genes} genes detected out of 2000 used for mapping.")
    # Subset adata object
    adata_sub = adata[:,genes].copy()
    # Pad object with 0 genes if needed
    if n_genes < 2000:
        diff = 2000 - n_genes
        print(f'Not all genes were recovered, filling in zeros for {diff} missing genes...')
        # Genes to pad with
        genes_to_add = set(ref_genes_df[gene_type].values).difference(set(adata_sub.var_names))
        df_padding = pd.DataFrame(data=np.zeros((adata_sub.shape[0],len(genes_to_add))), index=adata_sub.obs_names, columns=genes_to_add)
        adata_padding = sc.AnnData(df_padding)
        # Concatenate object
        adata_sub = anndata.concat([adata_sub, adata_padding], axis=1, join='outer', index_unique=None, merge='unique')
        # and order:
        adata_sub = adata_sub[:,ref_genes_df[gene_type]].copy()
    return adata_sub
