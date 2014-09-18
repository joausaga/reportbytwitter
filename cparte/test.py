from django.test import TestCase


class TestAppBehavior(TestCase):

    """
    Basic Test Scenarios
    """

    def test_manage_post_new_user_correct_answer_to_new_challenge(self):
        # Input: post from a new author and containing an expected answer
        # Output: a message asking for extra info
        pass

    def test_manage_post_new_user_incorrect_answer_to_new_challenge(self):
        # Input: post from a new author and containing an unexpected answer
        # Output: a message notifying the author that his/her contribution is in an incorrect format
        pass

    def test_manage_post_existing_user_correct_answer_to_new_challenge(self):
        # Input: post from an existing author and containing an expected answer
        # Output: a message thanking the author for his/her contribution
        pass

    def test_manage_post_existing_user_correct_answer_to_previously_answered_challenge(self):
        # Input: post from an existing author and containing an expected answer to a previously answered challenge
        # Output: a message asking the author to change his/her previous contribution
        pass

    def test_manage_post_existing_user_incorrect_answer_to_new_challenge(self):
        # Input: post from an existing author and containing an unexpected answer
        # Output: a message notifying the author that his/her contribution is in an incorrect format
        pass

    def test_manage_post_existing_user_incorrect_answer_to_previously_answered_challenge(self):
        # Input: post from an existing author and containing an expected answer
        # Output: a message notifying the author that his/her contribution is in an incorrect format
        pass

    """
    Test Scenarios for Replies
    """

    def test_manage_post_user_reply_wrongly_to_incorrect_answer_notification(self):
        # Input: reply from a new author and containing an unexpected answer
        # Output: a message notifying the author that his/her contribution is in an incorrect format
        pass

    def test_manage_post_user_reply_wrongly_n_times_in_a_row_to_incorrect_answer_notification(self):
        # Input: reply from a new author and containing an unexpected answer
        # Output: a message notifying the author has been banned
        pass

    def test_manage_post_new_user_reply_correctly_to_incorrect_answer_notification(self):
        # Input: reply from a new author and containing an unexpected answer
        # Output: a message asking for extra info
        pass

    def test_manage_post_new_user_reply_wrongly_to_extra_info_request(self):
        # Input: reply from a new author and containing an unexpected extra information
        # Output: a message notifying that the information provided is in an incorrect format asking to send it again
        pass

    def test_manage_post_new_user_reply_wrongly_n_times_in_a_row_to_extra_info_request(self):
        # Input: reply from a new author and containing an unexpected extra information
        # Output: a message notifying that his/her contribution cannot be saved
        pass

    def test_manage_post_new_user_reply_correctly_to_extra_info_request(self):
        # Input: reply from a new author and containing an expected extra information
        # Output: a message thanking for his/her contribution
        pass

    def test_manage_post_existing_user_reply_correctly_to_incorrect_answer_notification(self):
        # Input: reply from an existing author and containing an unexpected answer
        # Output: a message thanking for his/her contribution
        pass

    def test_manage_post_existing_user_reply_correctly_to_change_previous_contribution(self):
        # Input: reply from an existing author to a request about changing his/her previous contribution
        # Output: a message thanking the change
        pass

    def test_manage_post_existing_user_reply_wrongly_to_change_previous_contribution(self):
        # Input: reply from an existing author to a request about changing his/her previous contribution
        # Output: a message notifying that his/her answer couldn't be understood
        pass

    """
    Additional, more complex, Test Scenarios
    """

    def test_manage_post_only_the_correct_answer_is_saved(self):
        # Scenario:
        # An existing user post three post to three different challenges. Two of them are wrong and one correct.
        # Output: Check whether the saved contribution corresponds to the correct answer.
        pass

    def test_manage_post_only_one_permanent_contribution_per_user_per_challenge(self):
        # Scenario:
        # Post an answer to challenge 'X' as new user. Instead of replying the extra info, post an answer to challenge
        # 'Y' as a new user. This time answer correctly the extra info (the contribution to challenge 'Y' should be
        # saved) Post again an answer to challenge 'X' as new user since the extra info of the user is already known the
        # contribution should be saved and the first contribution to challenge 'X' should be delete
        # Output: Check whether exists only one contribution of the author for challenge X
        pass

    def test_manage_post_accept_correct_contribution_in_other_challenge(self):
        # Scenario:
        # As an existing user posts a wrong answer to challenge 'X'. As the same user posts a correct answer to
        # challenge 'Y'. Even when the first answer was rejected the second one should be accepted
        # Output: Check whether the contribution of the user to challenge 'Y' was saved
        pass

    def test_manage_post_new_user_post_new_answer_after_getting_a_request_for_extra_info(self):
        # Scenario:
        # A new user posts a correct answer to challenge 'X'. The app should reply asking for his/her extra information
        # but the user posts a new answer to challenge 'Y'. The app should reply again asking for his/her extra
        # information.
        # Output: Check whether both contributions are saved in 'temporal' mode
        pass

    def test_manage_post_discard_contribution_new_user(self):
        # Scenario:
        # A new user posts a correct answer to challenge 'X'. The app should reply asking for his/her extra information
        # but the user posts a new answer to challenge 'Y'. The app should reply again asking for his/her extra
        # information. The user answers wrongly n times in a row the request for extra info.
        # Output: Check whether the contributions to challenge 'Y' was deleted but the contribution to challenge 'X'
        # still exists in 'temporal' mode.
        pass

    def test_manage_post_existing_user_answer_twice_in_row_to_a_previously_answered_challenge(self):
        # Scenario:
        # An existing user posts a correct answer to the previously answered challenge 'X'. The app should reply asking
        # whether he/she wants to change his/her previously contribution. Instead of replying, the user posts again
        # a correct answer to the same challenge 'X' and the app should reply again asking to change his/her original
        # contribution with the second answer.
        # Output: Check whether exists two contribution from the user and if the temporal one corresponds to the
        # second post.
        pass

    def test_manage_post_exist_only_two_contributions_before_updating_the_original_contribution(self):
        # Scenario:
        # # An existing user posts a correct answer to the previously answered challenge 'X'. The app should reply asking
        # whether he/she wants to change his/her previously contribution. Instead of replying, the user posts again
        # a correct answer to the same challenge 'X' and the app should reply again asking to change his/her original
        # contribution with the second answer. This time the user replies correctly to the app answer.
        # Output: Check whether the original contribution was updated with the contribution sent in the second post.
        pass