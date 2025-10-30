import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  FlatList, 
  TouchableOpacity, 
  Alert, 
  StyleSheet,
  Modal,
  TextInput,
  ScrollView,
  ActivityIndicator,
  Platform
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import backend from '../../utils/backend'; // Adjust path to your backend.ts

// Types
interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  profession: string;
  specialist_type: string | null;
  discipline_id: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  approved_at: string | null;
}

interface ExamResult {
  id: number;
  user_id: number;
  user_email: string;
  user_name: string;
  user_profession: string;
  exam_id: string;
  exam_title: string;
  score: number;
  total_questions: number;
  percentage: number;
  passed: boolean;
  completed_at: string;
}

interface UserActivity {
  activity_type: string;
  timestamp: string;
  details: any;
}

type UserStatus = 'pending' | 'approved' | 'rejected';
type AdminTab = 'users' | 'exam-results' | 'dashboard';

export default function AdminScreen() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [examResults, setExamResults] = useState<ExamResult[]>([]);
  const [userActivities, setUserActivities] = useState<UserActivity[]>([]);
  const [filter, setFilter] = useState<UserStatus>('pending');
  const [activeTab, setActiveTab] = useState<AdminTab>('users');
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [passwordModalVisible, setPasswordModalVisible] = useState<boolean>(false);
  const [activityModalVisible, setActivityModalVisible] = useState<boolean>(false);
  const [newPassword, setNewPassword] = useState<string>('');
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [exporting, setExporting] = useState<boolean>(false);

  // Fetch users
  const fetchUsers = async (): Promise<void> => {
    try {
      const res = await backend.adminGetUsers(filter);
      if (res.ok) {
        setUsers(res.data || []);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to fetch users');
    }
  };

  // Fetch exam results
  const fetchExamResults = async (): Promise<void> => {
    try {
      const res = await backend.fetchWithAuth('/admin/exam-results');
      if (res.ok) {
        const results = res.data || [];
        setExamResults(results);
        // Auto-log to console for debugging
        logExamResultsToConsole(results);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to fetch exam results');
    }
  };

  // Fetch dashboard stats
  const fetchDashboardStats = async (): Promise<void> => {
    try {
      const res = await backend.fetchWithAuth('/admin/dashboard');
      if (res.ok) {
        setDashboardStats(res.data);
      }
    } catch (error) {
      console.log('Dashboard stats not available yet');
    }
  };

  // Fetch user activity
  const fetchUserActivity = async (userId: number): Promise<void> => {
    try {
      const res = await backend.fetchWithAuth(`/admin/users/${userId}/activity`);
      if (res.ok) {
        setUserActivities(res.data.activities || []);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to fetch user activity');
    }
  };

  // NEW: Log exam results to console
  const logExamResultsToConsole = (results?: ExamResult[]): void => {
    const dataToLog = results || examResults;
    
    if (dataToLog.length === 0) {
      console.log('No exam results to display');
      return;
    }

    console.log('=== EXAM RESULTS DEBUG INFO ===');
    console.log(`Total exam results: ${dataToLog.length}`);
    
    // Summary table
    console.table(dataToLog.map(result => ({
      'User': result.user_name,
      'Email': result.user_email,
      'Exam': result.exam_title,
      'Score': `${result.score}%`,
      'Passed': result.passed ? 'Yes' : 'No',
      'Completed': formatDate(result.completed_at)
    })));
    
    // Statistics
    const passedCount = dataToLog.filter(result => result.passed).length;
    const averageScore = dataToLog.reduce((sum, result) => sum + result.score, 0) / dataToLog.length;
    
    console.log('📊 Exam Statistics:');
    console.log(`- Pass Rate: ${((passedCount / dataToLog.length) * 100).toFixed(1)}%`);
    console.log(`- Average Score: ${averageScore.toFixed(1)}%`);
    console.log(`- Total Taken: ${dataToLog.length}`);
    console.log(`- Passed: ${passedCount}`);
    console.log(`- Failed: ${dataToLog.length - passedCount}`);
    
    // Detailed data
    console.log('📋 Detailed Exam Results:', dataToLog);
  };

  // FIXED: Export exam results to CSV - SIMPLIFIED
  const exportExamResultsToCSV = async (): Promise<void> => {
    if (examResults.length === 0) {
      Alert.alert('No Data', 'No exam results to export');
      return;
    }

    setExporting(true);
    
    try {
      // SIMPLIFIED: Only include Full Name, Exam Type, and Score
      const headers = 'Full Name,Exam Type,Score\n';
      const csvRows = examResults.map(result => 
        `"${result.user_name}","${result.exam_title}",${result.score}%`
      ).join('\n');
      
      const csvContent = headers + csvRows;
      
      // Check if we're on web or mobile with proper error handling
      if (Platform.OS === 'web') {
        // Web version: Create download link
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const timestamp = new Date().toISOString().split('T')[0];
        
        link.setAttribute('href', url);
        link.setAttribute('download', `exam_results_${timestamp}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        Alert.alert('Export Successful', 'Exam results downloaded as CSV file');
      } else {
        // Mobile version with safe encoding check
        const timestamp = new Date().toISOString().split('T')[0];
        const fileUri = FileSystem.documentDirectory + `exam_results_${timestamp}.csv`;
        
        // FIX: Safe encoding handling
        const encoding = FileSystem.EncodingType ? FileSystem.EncodingType.UTF8 : 'utf8';
        
        await FileSystem.writeAsStringAsync(fileUri, csvContent, {
          encoding: encoding
        });
        
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(fileUri, {
            mimeType: 'text/csv',
            dialogTitle: 'Export Exam Results',
            UTI: 'public.comma-separated-values-text'
          });
          Alert.alert('Export Successful', 'Exam results exported successfully!');
        } else {
          console.log('📁 CSV Export Content:\n', csvContent);
          Alert.alert('Export Ready', 'CSV content logged to console.');
        }
      }
    } catch (error) {
      console.error('Export failed:', error);
      Alert.alert('Export Failed', 'Failed to export exam results. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  // FIXED: Export users to CSV
  const exportUsersToCSV = async (): Promise<void> => {
    if (users.length === 0) {
      Alert.alert('No Data', 'No users to export');
      return;
    }

    setExporting(true);
    
    try {
      const headers = 'Name,Email,Profession,Specialty,Status,Created At,Approved At\n';
      const csvRows = users.map(user => 
        `"${user.full_name}","${user.email}","${getProfessionLabel(user.profession)}","${getSpecialistLabel(user.specialist_type)}","${user.status}","${user.created_at}","${user.approved_at || 'Not approved'}"`
      ).join('\n');
      
      const csvContent = headers + csvRows;
      
      // Check if we're on web or mobile
      if (Platform.OS === 'web') {
        // Web version: Create download link
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const timestamp = new Date().toISOString().split('T')[0];
        
        link.setAttribute('href', url);
        link.setAttribute('download', `users_${filter}_${timestamp}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        Alert.alert('Export Successful', 'Users data downloaded as CSV file');
      } else {
        // Mobile version with safe encoding
        const timestamp = new Date().toISOString().split('T')[0];
        const fileUri = FileSystem.documentDirectory + `users_${filter}_${timestamp}.csv`;
        
        const encoding = FileSystem.EncodingType ? FileSystem.EncodingType.UTF8 : 'utf8';
        
        await FileSystem.writeAsStringAsync(fileUri, csvContent, {
          encoding: encoding
        });
        
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(fileUri, {
            mimeType: 'text/csv',
            dialogTitle: `Export ${filter} Users`
          });
          Alert.alert('Export Successful', 'Users exported successfully!');
        } else {
          console.log('📁 Users CSV Content:\n', csvContent);
          Alert.alert('Export Ready', 'Users data logged to console.');
        }
      }
    } catch (error) {
      console.error('Export failed:', error);
      Alert.alert('Export Failed', 'Failed to export users data.');
    } finally {
      setExporting(false);
    }
  };

  // NEW: Simple console export for quick debugging
  const quickExportToConsole = (): void => {
    if (activeTab === 'exam-results' && examResults.length > 0) {
      console.log('📊 QUICK EXPORT - EXAM RESULTS:');
      console.table(examResults.map(result => ({
        'Full Name': result.user_name,
        'Exam Type': result.exam_title,
        'Score': `${result.score}%`
      })));
      Alert.alert('Console Export', 'Exam results logged to console as table');
    } else if (activeTab === 'users' && users.length > 0) {
      console.log('👥 QUICK EXPORT - USERS:');
      console.table(users.map(user => ({
        'Name': user.full_name,
        'Email': user.email,
        'Profession': getProfessionLabel(user.profession),
        'Specialty': getSpecialistLabel(user.specialist_type),
        'Status': user.status,
        'Created': formatDate(user.created_at),
        'Approved': user.approved_at ? formatDate(user.approved_at) : 'Not approved'
      })));
      Alert.alert('Console Export', 'Users data logged to console as table');
    } else {
      Alert.alert('No Data', 'No data available to export');
    }
  };

  const loadData = async (): Promise<void> => {
    setLoading(true);
    try {
      await fetchUsers();
      if (activeTab === 'exam-results') {
        await fetchExamResults();
      }
      if (activeTab === 'dashboard') {
        await fetchDashboardStats();
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const approveUser = async (userId: number): Promise<void> => {
    try {
      const res = await backend.adminApproveUser(userId);
      if (res.ok) {
        Alert.alert('Success', 'User approved successfully');
        fetchUsers();
      } else {
        Alert.alert('Error', res.data?.detail || 'Failed to approve user');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error');
    }
  };

  const rejectUser = async (userId: number): Promise<void> => {
    Alert.alert(
      'Reject User',
      'Are you sure you want to reject this user?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Reject', 
          style: 'destructive',
          onPress: async (): Promise<void> => {
            try {
              const res = await backend.adminRejectUser(userId);
              if (res.ok) {
                Alert.alert('Success', 'User rejected');
                fetchUsers();
              }
            } catch (error) {
              Alert.alert('Error', 'Network error');
            }
          }
        }
      ]
    );
  };

  // Reset user password
  const resetUserPassword = async (userId: number, password: string): Promise<void> => {
    try {
      const res = await backend.fetchWithAuth(`/admin/users/${userId}/reset-password`, {
        method: 'POST',
        body: JSON.stringify({ new_password: password })
      });
      
      if (res.ok) {
        Alert.alert('Success', 'Password reset successfully');
        setPasswordModalVisible(false);
        setNewPassword('');
      } else {
        Alert.alert('Error', 'Failed to reset password');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error');
    }
  };

  // Impersonate user
  const impersonateUser = async (userId: number): Promise<void> => {
    console.log('Starting impersonation for user:', userId);
    
    try {
      const res = await backend.fetchWithAuth(`/admin/users/${userId}/impersonate`, {
        method: 'POST'
      });
      
      console.log('Impersonation API response:', res);
      
      if (res.ok) {
        const { access_token, user } = res.data;
        console.log('Impersonation successful, storing tokens...');
        
        // Clear existing admin tokens first
        await AsyncStorage.multiRemove(['userToken', 'userData']);
        
        // Store the impersonation token and user data
        await AsyncStorage.setItem('userToken', access_token);
        await AsyncStorage.setItem('userData', JSON.stringify(user));
        
        console.log('Tokens stored successfully, navigating to main app...');
        
        Alert.alert('Success', `Now logged in as ${user.email}`, [
          {
            text: 'OK',
            onPress: () => {
              console.log('Navigating to main app...');
              // Navigate to main app as this user
              router.replace('/(tabs)');
            }
          }
        ]);
        
      } else {
        console.error('Impersonation failed with status:', res.status, res.data);
        Alert.alert('Error', res.data?.detail || `Failed to impersonate user (Status: ${res.status})`);
      }
    } catch (error) {
      console.error('Impersonation error:', error);
      Alert.alert('Error', `Failed to impersonate user: ${error}`);
    }
  };

  // View user activity
  const viewUserActivity = async (user: User): Promise<void> => {
    setSelectedUser(user);
    await fetchUserActivity(user.id);
    setActivityModalVisible(true);
  };

  const handleRefresh = (): void => {
    setRefreshing(true);
    loadData();
  };

  useEffect(() => {
    loadData();
  }, [filter, activeTab]);

  const getStatusColor = (status: UserStatus): string => {
    switch (status) {
      case 'pending': return '#f59e0b';
      case 'approved': return '#10b981';
      case 'rejected': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getProfessionLabel = (profession: string): string => {
    const professionMap: { [key: string]: string } = {
      'gp': 'General Practitioner',
      'nurse': 'Nurse',
      'midwife': 'Midwife',
      'lab_tech': 'Lab Technologist',
      'physiotherapist': 'Physiotherapist',
      'specialist_nurse': 'Specialist Nurse'
    };
    return professionMap[profession] || profession;
  };

  const getSpecialistLabel = (specialistType: string | null): string => {
    if (!specialistType) return '';
    
    const specialistMap: { [key: string]: string } = {
      'icu_nurse': 'ICU Nurse',
      'emergency_nurse': 'Emergency Nurse',
      'neonatal_nurse': 'Neonatal Nurse',
      'other': 'Other Specialty'
    };
    return specialistMap[specialistType] || specialistType;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // UPDATED: Render exam results with full name prominently displayed
  const renderExamResultItem = ({ item }: { item: ExamResult }): JSX.Element => (
    <View style={styles.examCard}>
      <View style={styles.examHeader}>
        <Text style={styles.examTitle}>{item.exam_title}</Text>
        <View style={[styles.scoreBadge, { backgroundColor: item.passed ? '#10b981' : '#ef4444' }]}>
          <Text style={styles.scoreText}>{item.score}%</Text>
        </View>
      </View>
      
      {/* UPDATED: Added full name display */}
      <Text style={styles.examUserName}>Candidate: {item.user_name}</Text>
      <Text style={styles.examUser}>Email: {item.user_email}</Text>
      <Text style={styles.examInfo}>Profession: {getProfessionLabel(item.user_profession)}</Text>
      <Text style={styles.examInfo}>Completed: {formatDate(item.completed_at)}</Text>
      <Text style={styles.examInfo}>
        Score: {item.score}% ({item.passed ? 'Passed' : 'Failed'})
      </Text>
      <Text style={styles.examInfo}>Total Questions: {item.total_questions}</Text>
    </View>
  );

  // Render user activity
  const renderActivityItem = ({ item }: { item: UserActivity }): JSX.Element => (
    <View style={styles.activityCard}>
      <Text style={styles.activityType}>{item.activity_type}</Text>
      <Text style={styles.activityTime}>{formatDate(item.timestamp)}</Text>
      {item.details && (
        <Text style={styles.activityDetails}>
          {JSON.stringify(item.details, null, 2)}
        </Text>
      )}
    </View>
  );

  // Render user item with new actions
  const renderUserItem = ({ item }: { item: User }): JSX.Element => (
    <View style={styles.userCard}>
      <View style={styles.userHeader}>
        <Text style={styles.userName}>{item.full_name}</Text>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
          <Text style={styles.statusText}>{item.status.toUpperCase()}</Text>
        </View>
      </View>
      
      <Text style={styles.userEmail}>{item.email}</Text>
      <Text style={styles.userInfo}>Profession: {getProfessionLabel(item.profession)}</Text>
      {item.specialist_type && (
        <Text style={styles.userInfo}>Specialty: {getSpecialistLabel(item.specialist_type)}</Text>
      )}
      <Text style={styles.userInfo}>Registered: {formatDate(item.created_at)}</Text>

      {/* Action Buttons */}
      <View style={styles.actionButtons}>
        {item.status === 'pending' ? (
          <>
            <TouchableOpacity 
              style={styles.approveButton}
              onPress={() => approveUser(item.id)}
            >
              <Text style={styles.buttonText}>Approve</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.rejectButton}
              onPress={() => rejectUser(item.id)}
            >
              <Text style={styles.buttonText}>Reject</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            <TouchableOpacity 
              style={styles.secondaryButton}
              onPress={() => viewUserActivity(item)}
            >
              <Text style={styles.buttonText}>Activity</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.secondaryButton}
              onPress={() => {
                setSelectedUser(item);
                setPasswordModalVisible(true);
              }}
            >
              <Text style={styles.buttonText}>Reset PW</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.primaryButton}
              onPress={() => {
                console.log('Login As button pressed for user:', item.id, item.email);
                impersonateUser(item.id);
              }}
            >
              <Text style={styles.buttonText}>Login As</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </View>
  );

  // Dashboard view
  const renderDashboard = (): JSX.Element => {
    if (!dashboardStats) {
      return (
        <View style={styles.centered}>
          <Text>Loading dashboard...</Text>
        </View>
      );
    }

    return (
      <ScrollView>
        <View style={styles.statsContainer}>
          <Text style={styles.sectionTitle}>User Statistics</Text>
          <View style={styles.statsGrid}>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{dashboardStats.user_stats.total_users}</Text>
              <Text style={styles.statLabel}>Total Users</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{dashboardStats.user_stats.pending_approval}</Text>
              <Text style={styles.statLabel}>Pending</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{dashboardStats.user_stats.approved_users}</Text>
              <Text style={styles.statLabel}>Approved</Text>
            </View>
          </View>

          <Text style={styles.sectionTitle}>Exam Statistics</Text>
          <View style={styles.statsGrid}>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{dashboardStats.exam_stats.total_exams_taken}</Text>
              <Text style={styles.statLabel}>Exams Taken</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{dashboardStats.exam_stats.passed_exams}</Text>
              <Text style={styles.statLabel}>Passed</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>
                {Math.round(dashboardStats.exam_stats.pass_rate)}%
              </Text>
              <Text style={styles.statLabel}>Pass Rate</Text>
            </View>
          </View>

          <Text style={styles.sectionTitle}>Recent Activity</Text>
          {dashboardStats.recent_activity.map((activity: any, index: number) => (
            <View key={index} style={styles.activityItem}>
              <Text style={styles.activityUser}>{activity.user_email}</Text>
              <Text style={styles.activityAction}>{activity.activity_type}</Text>
              <Text style={styles.activityTime}>{formatDate(activity.timestamp)}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    );
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header with enhanced debug feature */}
      <TouchableOpacity 
        onLongPress={() => {
          console.log('=== ADMIN PANEL DEBUG ===');
          console.log('Active Tab:', activeTab);
          console.log('Users count:', users.length);
          console.log('Exam results count:', examResults.length);
          console.log('Filter:', filter);
          console.log('Platform:', Platform.OS);
          Alert.alert('Debug', `Platform: ${Platform.OS}\nCheck console for details`);
        }}
        delayLongPress={2000}
      >
        <Text style={styles.title}>Admin Dashboard</Text>
        <Text style={styles.subtitle}>Platform: {Platform.OS}</Text>
      </TouchableOpacity>
      
      {/* Tab Navigation */}
      <View style={styles.tabContainer}>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'users' && styles.activeTab]}
          onPress={() => setActiveTab('users')}
        >
          <Text style={[styles.tabText, activeTab === 'users' && styles.activeTabText]}>
            Users
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'exam-results' && styles.activeTab]}
          onPress={() => setActiveTab('exam-results')}
        >
          <Text style={[styles.tabText, activeTab === 'exam-results' && styles.activeTabText]}>
            Exam Results
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'dashboard' && styles.activeTab]}
          onPress={() => setActiveTab('dashboard')}
        >
          <Text style={[styles.tabText, activeTab === 'dashboard' && styles.activeTabText]}>
            Dashboard
          </Text>
        </TouchableOpacity>
      </View>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <>
          <View style={styles.filterContainer}>
            <TouchableOpacity 
              style={[styles.filterButton, filter === 'pending' && styles.filterActive]}
              onPress={() => setFilter('pending')}
            >
              <Text style={[styles.filterText, filter === 'pending' && styles.filterTextActive]}>
                Pending
              </Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.filterButton, filter === 'approved' && styles.filterActive]}
              onPress={() => setFilter('approved')}
            >
              <Text style={[styles.filterText, filter === 'approved' && styles.filterTextActive]}>
                Approved
              </Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.filterButton, filter === 'rejected' && styles.filterActive]}
              onPress={() => setFilter('rejected')}
            >
              <Text style={[styles.filterText, filter === 'rejected' && styles.filterTextActive]}>
                Rejected
              </Text>
            </TouchableOpacity>

            {/* Export Users Button */}
            {users.length > 0 && (
              <View style={styles.exportButtonsContainer}>
                <TouchableOpacity 
                  style={[styles.exportButton, exporting && styles.disabledButton]}
                  onPress={exportUsersToCSV}
                  disabled={exporting}
                >
                  {exporting ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <Text style={styles.exportButtonText}>
                      {Platform.OS === 'web' ? 'Download CSV' : 'Export CSV'}
                    </Text>
                  )}
                </TouchableOpacity>
                
                <TouchableOpacity 
                  style={[styles.consoleExportButton, exporting && styles.disabledButton]}
                  onPress={quickExportToConsole}
                  disabled={exporting}
                >
                  <Text style={styles.consoleExportButtonText}>Console Table</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>

          <FlatList
            data={users}
            keyExtractor={(item) => item.id.toString()}
            renderItem={renderUserItem}
            contentContainerStyle={styles.listContainer}
            refreshing={refreshing}
            onRefresh={handleRefresh}
            ListEmptyComponent={
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>No {filter} users found</Text>
              </View>
            }
          />
        </>
      )}

      {/* Exam Results Tab */}
      {activeTab === 'exam-results' && (
        <>
          {/* Export Header */}
          {examResults.length > 0 && (
            <View style={styles.exportHeader}>
              <Text style={styles.resultsCount}>
                {examResults.length} exam result(s) found
              </Text>
              <View style={styles.exportButtonsContainer}>
                <TouchableOpacity 
                  style={[styles.exportButton, exporting && styles.disabledButton]}
                  onPress={exportExamResultsToCSV}
                  disabled={exporting}
                >
                  {exporting ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <Text style={styles.exportButtonText}>
                      {Platform.OS === 'web' ? 'Download CSV' : 'Export CSV'}
                    </Text>
                  )}
                </TouchableOpacity>
                
                <TouchableOpacity 
                  style={[styles.consoleExportButton, exporting && styles.disabledButton]}
                  onPress={quickExportToConsole}
                  disabled={exporting}
                >
                  <Text style={styles.consoleExportButtonText}>Console Table</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          <FlatList
            data={examResults}
            keyExtractor={(item) => item.id.toString()}
            renderItem={renderExamResultItem}
            contentContainerStyle={styles.listContainer}
            refreshing={refreshing}
            onRefresh={handleRefresh}
            ListEmptyComponent={
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>No exam results found</Text>
              </View>
            }
          />
        </>
      )}

      {/* Dashboard Tab */}
      {activeTab === 'dashboard' && renderDashboard()}

      {/* Password Reset Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={passwordModalVisible}
        onRequestClose={() => setPasswordModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Reset Password</Text>
            <Text style={styles.modalSubtitle}>
              For user: {selectedUser?.email}
            </Text>
            
            <TextInput
              style={styles.input}
              placeholder="Enter new password"
              value={newPassword}
              onChangeText={setNewPassword}
              secureTextEntry
            />
            
            <View style={styles.modalButtons}>
              <TouchableOpacity 
                style={styles.cancelButton}
                onPress={() => setPasswordModalVisible(false)}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              
              <TouchableOpacity 
                style={[styles.confirmButton, !newPassword && styles.disabledButton]}
                onPress={() => selectedUser && resetUserPassword(selectedUser.id, newPassword)}
                disabled={!newPassword}
              >
                <Text style={styles.confirmButtonText}>Reset Password</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* User Activity Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={activityModalVisible}
        onRequestClose={() => setActivityModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={[styles.modalContent, styles.largeModal]}>
            <Text style={styles.modalTitle}>
              User Activity: {selectedUser?.email}
            </Text>
            
            <FlatList
              data={userActivities}
              keyExtractor={(item, index) => index.toString()}
              renderItem={renderActivityItem}
              style={styles.activityList}
              ListEmptyComponent={
                <Text style={styles.emptyText}>No activity found for this user</Text>
              }
            />
            
            <TouchableOpacity 
              style={styles.closeButton}
              onPress={() => setActivityModalVisible(false)}
            >
              <Text style={styles.closeButtonText}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#1a365d',
  },
  subtitle: {
    fontSize: 12,
    color: '#6b7280',
    textAlign: 'center',
    marginTop: -5,
    marginBottom: 10,
  },
  tabContainer: {
    flexDirection: 'row',
    marginBottom: 20,
    backgroundColor: '#f3f4f6',
    borderRadius: 8,
    padding: 4,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 6,
  },
  activeTab: {
    backgroundColor: '#007AFF',
  },
  tabText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#374151',
  },
  activeTabText: {
    color: '#fff',
  },
  filterContainer: {
    flexDirection: 'row',
    marginBottom: 20,
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  filterButton: {
    flex: 1,
    paddingHorizontal: 8,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#f3f4f6',
    marginHorizontal: 4,
    alignItems: 'center',
  },
  filterActive: {
    backgroundColor: '#007AFF',
  },
  filterText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#374151',
    textAlign: 'center',
  },
  filterTextActive: {
    color: '#fff',
  },
  exportHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingHorizontal: 4,
  },
  exportButtonsContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  exportButton: {
    backgroundColor: '#059669',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 6,
    minWidth: 80,
    alignItems: 'center',
  },
  consoleExportButton: {
    backgroundColor: '#6366f1',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 6,
    minWidth: 80,
    alignItems: 'center',
  },
  consoleExportButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  disabledButton: {
    backgroundColor: '#9ca3af',
    opacity: 0.7,
  },
  exportButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  resultsCount: {
    fontSize: 14,
    color: '#6b7280',
    fontWeight: '500',
  },
  listContainer: {
    paddingBottom: 20,
  },
  userCard: {
    backgroundColor: '#f8fafc',
    padding: 16,
    marginBottom: 12,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  userHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  userName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1e293b',
    flex: 1,
    marginRight: 8,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    minWidth: 70,
    alignItems: 'center',
  },
  statusText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  userEmail: {
    fontSize: 14,
    color: '#475569',
    marginBottom: 4,
    fontWeight: '500',
  },
  userInfo: {
    fontSize: 12,
    color: '#64748b',
    marginBottom: 2,
  },
  actionButtons: {
    flexDirection: 'row',
    marginTop: 12,
    gap: 8,
  },
  approveButton: {
    flex: 1,
    backgroundColor: '#10b981',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  rejectButton: {
    flex: 1,
    backgroundColor: '#ef4444',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  primaryButton: {
    flex: 1,
    backgroundColor: '#007AFF',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: '#6b7280',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  examCard: {
    backgroundColor: '#f0f9ff',
    padding: 16,
    marginBottom: 12,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#0ea5e9',
  },
  examHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  examTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0c4a6e',
    flex: 1,
    marginRight: 8,
  },
  scoreBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    minWidth: 50,
    alignItems: 'center',
  },
  scoreText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  // NEW: Style for the full name
  examUserName: {
    fontSize: 15,
    color: '#1e293b',
    marginBottom: 4,
    fontWeight: '600',
  },
  examUser: {
    fontSize: 14,
    color: '#475569',
    marginBottom: 4,
    fontWeight: '500',
  },
  examInfo: {
    fontSize: 12,
    color: '#64748b',
    marginBottom: 2,
  },
  statsContainer: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#1e293b',
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#f8fafc',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: 4,
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#64748b',
    textAlign: 'center',
  },
  activityItem: {
    backgroundColor: '#f8fafc',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  activityUser: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#1e293b',
  },
  activityAction: {
    fontSize: 12,
    color: '#475569',
    textTransform: 'capitalize',
  },
  activityTime: {
    fontSize: 10,
    color: '#64748b',
  },
  activityCard: {
    backgroundColor: '#f8fafc',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  activityType: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#1e293b',
    textTransform: 'capitalize',
  },
  activityTime: {
    fontSize: 12,
    color: '#64748b',
    marginBottom: 4,
  },
  activityDetails: {
    fontSize: 10,
    color: '#475569',
    fontFamily: 'monospace',
  },
  activityList: {
    maxHeight: 400,
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    width: '80%',
    maxWidth: 400,
  },
  largeModal: {
    width: '90%',
    maxHeight: '80%',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
    textAlign: 'center',
  },
  modalSubtitle: {
    fontSize: 14,
    color: '#64748b',
    marginBottom: 16,
    textAlign: 'center',
  },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    fontSize: 16,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#6b7280',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  confirmButton: {
    flex: 1,
    backgroundColor: '#007AFF',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  confirmButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  closeButton: {
    backgroundColor: '#6b7280',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 16,
  },
  closeButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    textAlign: 'center',
    fontSize: 16,
    color: '#6b7280',
    marginTop: 20,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
  },
});