"""
This script is used to cluster the sensor data of the ADL dataset.
the clustering is performed with a brute force approach, i.e. ignoring the kind of sensor data. 
"""
import numpy as np
import pandas as pd
import seaborn as sns

import sys, os
sys.path.insert(0, '../')
from dfHelper import*

import argparse
argparser = argparse.ArgumentParser()
argparser.add_argument('--subject', type=int, default=1)
argparser.add_argument('--run', type=int, default=2)
argparser.add_argument('--sensor_type', type=str, default='all')
argparser.add_argument('--metric', type=str, default='euclidean')

def main(subject, run, sensor_type, metric):
    """
    filter locomotion data for each sensor type and cluster them
    the idea is that we want to show if clustering and taking the centers allows to distinguish between standing and walking.
     
    parameters:
        subject: index of the subject
        run: dataset index for a given subject
        sensor_type: type of sensor to be clustered
    """
    if not sensor_type in {'triaxial_acc', 'IMU_acc', 'IMU_gyro', 'IMU_mag', 'all'}:
        raise ValueError('sensor_type must be one of the following: "triaxial_acc", "IMU_acc", "IMU_gyro", "IMU_mag", "all"')
   
    data = load_data_adl(subject, run, '../OpportunityUCIDataset')
    df_LW = get_locomotion_data(data, [2, 5])

    if sensor_type != 'all':
        lie_walk = get_sensor_data(df_LW, sensor_type)
    else:
        # IMU RUA, RLA, BACK
        # triaxial: hip, back, RUA^, RUA_, RWR, RKN_
        imu_acc = load_data_adl(subject, run, '../OpportunityUCIDataset')
        imu_gyro = load_data_adl(subject, run, '../OpportunityUCIDataset')
        triaxial_acc = load_data_adl(subject, run, '../OpportunityUCIDataset')
        imu_acc = get_sensor_data(imu_acc, 'IMU_acc')
        imu_gyro = get_sensor_data(imu_gyro, 'IMU_gyro')
        triaxial_acc = get_sensor_data(triaxial_acc, 'triaxial_acc')

        extra_cols = imu_acc[imu_acc.columns[-8:]]
        lie_walk = imu_acc[imu_acc.columns[:-8]]
        lie_walk = lie_walk.join(imu_gyro[imu_gyro.columns[:-8]])
        lie_walk = lie_walk.join(triaxial_acc[triaxial_acc.columns[:-8]])
        cols = lie_walk.columns.tolist()
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        lie_walk = scaler.fit_transform(lie_walk)
        lie_walk = pd.DataFrame(lie_walk, columns=cols)
        lie_walk = lie_walk.join(extra_cols)

    

    print (lie_walk.columns)
    #############################################################################
    #           Clustering: apply clustering for each time step                 #
    #############################################################################
    from sklearn.cluster import KMeans
    from tslearn.clustering import TimeSeriesKMeans

    train = lie_walk[lie_walk.columns[:-6]] #keep only locomotion as label
    lie_train = train[train['Locomotion'] == 5].drop(['Locomotion'], axis=1)
    timeL = lie_train['MILLISEC'].values
    lie_train = lie_train.drop(['MILLISEC'], axis=1)

    walk_train = train[train['Locomotion'] == 2].drop(['Locomotion'], axis=1)
    timeW = walk_train['MILLISEC'].values
    walk_train = walk_train.drop(['MILLISEC'], axis=1)

    # create all folders
    if not os.path.isdir('clustering_results_{}/subject_{}'.format(metric, subject)): 
        os.makedirs('clustering_results_{}/subject_{}'.format(metric,subject))
    if not os.path.isdir('clustering_results_{}/subject_{}/run_{}'.format(metric,subject, run)): 
        os.makedirs('clustering_results_{}/subject_{}/run_{}'.format(metric,subject, run))
    if not os.path.isdir('clustering_results_{}/subject_{}/run_{}/laying'.format(metric,subject, run)):
        os.makedirs('clustering_results_{}/subject_{}/run_{}/laying'.format(metric,subject, run))
    if not os.path.isdir('clustering_results_{}/subject_{}/run_{}/walking'.format(metric,subject, run)):
        os.makedirs('clustering_results_{}/subject_{}/run_{}/walking'.format(metric,subject, run))
    if not os.path.isdir('clustering_results_{}/subject_{}/run_{}/laying/sensor_type_{}'.format(metric,subject, run, sensor_type)):
        os.makedirs('clustering_results_{}/subject_{}/run_{}/laying/sensor_type_{}'.format(metric,subject, run, sensor_type))
    if not os.path.isdir('clustering_results_{}/subject_{}/run_{}/walking/sensor_type_{}'.format(metric,subject, run, sensor_type)):
        os.makedirs('clustering_results_{}/subject_{}/run_{}/walking/sensor_type_{}'.format(metric,subject, run, sensor_type))

    #############################################################################
    nclusters = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    if not os.path.isdir('clustering_results_{}'.format(metric)): os.mkdir('clustering_results_{}'.format(metric))

    # laying DATA
    print("laying data")
    for n in nclusters:
        lie_centers, lie_scores, lie_time = [], [], []

        print(f'n = {n}')
        for i in range(lie_train.shape[0]):
            if i%300==0: print("iteration {} of {}".format(i, lie_train.shape[0]))
            data = lie_train.iloc[i,:].values.reshape(-1, 1)
            # check if data contains NaN, if its the case skip it
            if np.isnan(data).any(): 
                continue
            kmeans = TimeSeriesKMeans(n_clusters=n).fit(data)
            lie_centers.append(kmeans.cluster_centers_)
            lie_scores.append(kmeans.inertia_)

            lie_time.append(timeL[i])

        LCenters = np.array(lie_centers).reshape(-1, n)
        df_lie_centers = pd.DataFrame(LCenters, columns = ['center {}'.format(i) for i in range(n)])
        df_lie_centers['score'] = lie_scores
        df_lie_centers['MILLISEC'] = lie_time
        df_lie_centers = df_lie_centers.sort_values(by='MILLISEC')
        df_lie_centers.reset_index(drop=True, inplace=True)
        df_lie_centers.to_csv('clustering_results_{}/subject_{}/run_{}/laying/sensor_type_{}/{}_clusters.csv'\
                            .format(metric, subject, run, sensor_type, n), index=False)
    # WALKING DATA
    print("Walking data")
    for n in nclusters:
        walk_centers, walk_scores, walk_time = [], [], []
        for i in range(walk_train.shape[0]):
            if i%600==0: print("iteration {} of {}".format(i, walk_train.shape[0]))
            data = walk_train.iloc[i, :].values.reshape(-1, 1)
            # check if data contains NaN, if its the case skip it
            if np.isnan(data).any(): 
                continue
            kmeans = TimeSeriesKMeans(n_clusters=n).fit(data)
            walk_centers.append(kmeans.cluster_centers_)
            walk_scores.append(kmeans.inertia_)
            walk_time.append(timeW[i])
            
        WCenters = np.array(walk_centers).reshape(-1, n)
        df_walk_centers = pd.DataFrame(WCenters, columns = ['centers {}'.format(i) for i in range(n)])
        df_walk_centers['score'] = walk_scores
        df_walk_centers['MILLISEC'] = walk_time
        df_walk_centers = df_walk_centers.sort_values(by='MILLISEC')
        df_walk_centers.reset_index(drop=True, inplace=True)
        df_walk_centers.to_csv('clustering_results_{}/subject_{}/run_{}/walking/sensor_type_{}/{}_clusters.csv'\
                        .format(metric, subject, run, sensor_type, n), index=False)



if __name__ == '__main__':
    args = vars(argparser.parse_args())
    main(**args)