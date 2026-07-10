public final class LedgerReportService {
    private final LedgerRepository repository;

    public LedgerReportService(LedgerRepository repository) {
        this.repository = repository;
    }

    public Report getReport(String accountId) {
        try {
            return repository.findAll(accountId);
        } catch (Exception exception) {
            return null;
        }
    }
}
